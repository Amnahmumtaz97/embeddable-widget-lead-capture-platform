from copy import deepcopy
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.config import Settings
from app.services.rate_limit import SlidingWindowRateLimiter


TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


class FakeGeo:
    def enrich(self, ip):
        return {"country": "Pakistan", "country_code": "PK", "city": "Karachi", "provider": "provider_b"}


class FakeAuth:
    def __init__(self):
        self.logged_out = []

    def signup(self, email, password):
        return {"user": {"id": "user-1", "email": email, "created_at": "2026-09-29T00:00:00Z"}}

    def login(self, email, password):
        if password != "password123":
            from app.services.auth import AuthProviderError
            raise AuthProviderError("bad login", 400)
        return {"access_token": "valid-jwt", "refresh_token": "refresh-jwt", "token_type": "bearer", "expires_in": 3600, "user": {"id": "user-1", "email": email}}

    def refresh(self, refresh_token):
        if refresh_token != "refresh-jwt":
            from app.services.auth import AuthProviderError
            raise AuthProviderError("bad refresh", 400)
        return {"access_token": "new-jwt", "refresh_token": "new-refresh", "token_type": "bearer"}

    def verify(self, token):
        if token not in {"valid-jwt", "new-jwt"}:
            from app.services.auth import AuthProviderError
            raise AuthProviderError("bad token", 401)
        return {"id": "user-1", "email": "test@example.com", "created_at": "2026-09-29T00:00:00Z"}

    def logout(self, token):
        self.logged_out.append(token)


class MemoryRepository:
    def __init__(self):
        self.tenants = {"key-a": {"id": TENANT_A, "name": "Tenant A"}, "key-b": {"id": TENANT_B, "name": "Tenant B"}}
        self.widgets = {}
        self.submissions = []
        self.jobs = []

    def migrate(self):
        return None

    def tenant_for_api_key(self, key):
        return self.tenants.get(key)

    def create_widget(self, tenant_id, payload):
        now = datetime.now(timezone.utc)
        row = {"id": uuid4(), "tenant_id": tenant_id, "form_fields": deepcopy(payload["fields"]), "active": True, "created_at": now, "updated_at": now, **{k: deepcopy(v) for k, v in payload.items() if k != "fields"}}
        self.widgets[row["id"]] = row
        return deepcopy(row)

    def list_widgets(self, tenant_id):
        return [deepcopy(w) for w in self.widgets.values() if w["tenant_id"] == tenant_id]

    def get_widget(self, tenant_id, widget_id):
        widget = self.widgets.get(widget_id)
        return deepcopy(widget) if widget and widget["tenant_id"] == tenant_id else None

    def get_public_widget(self, widget_id):
        widget = self.widgets.get(widget_id)
        return deepcopy(widget) if widget and widget["active"] else None

    def update_widget(self, tenant_id, widget_id, payload):
        widget = self.widgets.get(widget_id)
        if not widget or widget["tenant_id"] != tenant_id:
            return None
        widget.update({k: deepcopy(v) for k, v in payload.items() if k != "fields"})
        widget["form_fields"] = deepcopy(payload["fields"])
        widget["updated_at"] = datetime.now(timezone.utc)
        return deepcopy(widget)

    def delete_widget(self, tenant_id, widget_id):
        if not self.get_widget(tenant_id, widget_id):
            return False
        del self.widgets[widget_id]
        return True

    def find_submission_by_idempotency(self, widget_id, key):
        return next((deepcopy(s) for s in self.submissions if s["widget_id"] == widget_id and s["idempotency_key"] == key), None)

    def create_submission_with_job(self, *, widget, data, ip_address, geo, idempotency_key):
        existing = self.find_submission_by_idempotency(widget["id"], idempotency_key) if idempotency_key else None
        if existing:
            return existing, False
        row = {"id": uuid4(), "tenant_id": widget["tenant_id"], "widget_id": widget["id"], "data": deepcopy(data), "ip_address": ip_address, "idempotency_key": idempotency_key, "created_at": datetime.now(timezone.utc), "country": geo.get("country") if geo else None, "country_code": geo.get("country_code") if geo else None, "city": geo.get("city") if geo else None, "geo_provider": geo.get("provider") if geo else None}
        self.submissions.append(row)
        self.jobs.append({"id": uuid4(), "submission_id": row["id"], "payload": {"submission_id": str(row["id"])}, "status": "pending", "attempts": 0, "max_attempts": 3})
        return deepcopy(row), True

    def list_submissions(self, tenant_id, limit=100):
        return [deepcopy(s) for s in self.submissions if s["tenant_id"] == tenant_id][:limit]

    def dashboard_stats(self, tenant_id):
        rows = [s for s in self.submissions if s["tenant_id"] == tenant_id]
        per_widget = []
        for widget in self.list_widgets(tenant_id):
            per_widget.append({"widget_id": widget["id"], "title": widget["title"], "count": sum(s["widget_id"] == widget["id"] for s in rows)})
        geo = []
        for country in sorted({s["country"] or "Unknown" for s in rows}):
            geo.append({"country": country, "count": sum((s["country"] or "Unknown") == country for s in rows)})
        return {"total": len(rows), "per_widget": per_widget, "over_time": [{"date": date.today(), "count": len(rows)}] if rows else [], "geo": geo}

    def claim_jobs(self, limit=10):
        claimed = []
        for job in self.jobs:
            if job["status"] in {"pending", "retry"}:
                job["status"] = "processing"
                job["attempts"] += 1
                claimed.append(deepcopy(job))
        return claimed[:limit]

    def complete_job(self, job_id):
        next(j for j in self.jobs if j["id"] == job_id)["status"] = "completed"

    def fail_job(self, job_id, error, terminal):
        job = next(j for j in self.jobs if j["id"] == job_id)
        job["status"] = "failed" if terminal else "retry"
        job["last_error"] = error


WIDGET_PAYLOAD = {"type": "contact", "title": "Talk to us", "description": "We reply quickly.", "fields": [{"name": "email", "label": "Email", "type": "email", "required": True, "max_length": 120}, {"name": "message", "label": "Message", "type": "textarea", "required": True, "max_length": 500}], "button_text": "Send", "display_options": {"theme": "light"}}


@pytest.fixture
def app_factory():
    clients = []
    def make(*, ip_limit=20, widget_limit=100, max_payload=16384, geo=None, auth=None):
        repo = MemoryRepository()
        settings = Settings(public_base_url="http://testserver", worker_enabled=False, trust_proxy_headers=True, rate_limit_ip=ip_limit, rate_limit_widget=widget_limit, max_payload_bytes=max_payload)
        limiter = SlidingWindowRateLimiter(ip_limit, widget_limit, 60)
        app = create_app(settings=settings, repository=repo, geo_enricher=geo or FakeGeo(), rate_limiter=limiter, auth_service=auth or FakeAuth(), start_worker=False)
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        return client, repo
    yield make
    for client in clients:
        client.__exit__(None, None, None)
