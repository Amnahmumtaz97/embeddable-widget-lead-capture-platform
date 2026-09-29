from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.config import Settings, get_settings
from app.models import SubmissionCreate, WidgetCreate, WidgetUpdate
from app.repositories import PostgresRepository, jsonable_row
from app.services.geo import GeoEnricher
from app.services.jobs import ConsoleNotifier, JobWorker
from app.services.rate_limit import RateLimitExceeded, SlidingWindowRateLimiter
from app.services.submissions import validate_submission_data


BASE_DIR = Path(__file__).resolve().parent.parent
WIDGET_BUNDLE = BASE_DIR / "assets" / "widget.v1.js"


class PayloadSizeMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        declared = headers.get(b"content-length")
        if declared:
            try:
                if int(declared) > self.max_bytes:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse(status_code=400, content={"error": "Invalid Content-Length"})
                await response(scope, receive, send)
                return
        chunks: list[bytes] = []
        total = 0
        more = True
        while more:
            message = await receive()
            body = message.get("body", b"")
            total += len(body)
            if total > self.max_bytes:
                await self._reject(scope, receive, send)
                return
            chunks.append(body)
            more = message.get("more_body", False)
        replayed = False

        async def replay_receive():
            nonlocal replayed
            if replayed:
                return {"type": "http.request", "body": b"", "more_body": False}
            replayed = True
            return {"type": "http.request", "body": b"".join(chunks), "more_body": False}

        await self.app(scope, replay_receive, send)

    async def _reject(self, scope, receive, send):
        response = JSONResponse(status_code=413, content={"error": "Payload too large"})
        await response(scope, receive, send)


def _dump_widget(widget: dict[str, Any]) -> dict[str, Any]:
    row = jsonable_row(widget)
    row["fields"] = row.pop("form_fields")
    return row


def create_app(*, settings: Settings | None = None, repository=None, geo_enricher=None, rate_limiter=None, start_worker: bool | None = None) -> FastAPI:
    settings = settings or get_settings()
    repository = repository or PostgresRepository(settings.database_url)
    geo_enricher = geo_enricher or GeoEnricher(settings)
    rate_limiter = rate_limiter or SlidingWindowRateLimiter(settings.rate_limit_ip, settings.rate_limit_widget, settings.rate_limit_window_seconds)
    worker = JobWorker(repository, ConsoleNotifier(settings.notification_force_failure), settings)
    should_start_worker = settings.worker_enabled if start_worker is None else start_worker

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        repository.migrate()
        if should_start_worker:
            worker.start()
        yield
        if should_start_worker:
            worker.stop()

    app = FastAPI(title="Embeddable Widget & Lead-Capture Platform", version="1.0.0", lifespan=lifespan)
    app.state.repository = repository
    app.state.worker = worker
    app.add_middleware(PayloadSizeMiddleware, max_bytes=settings.max_payload_bytes)
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "X-API-Key", "Idempotency-Key", "Authorization"], expose_headers=["X-Idempotent-Replay", "Retry-After"], max_age=600)

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        content = exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content=jsonable_encoder({"error": "Invalid request", "details": exc.errors()}))

    def current_tenant(x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> dict[str, Any]:
        key = x_api_key
        if not key and authorization and authorization.lower().startswith("bearer "):
            key = authorization[7:].strip()
        if not key:
            raise HTTPException(401, detail={"error": "Authentication required"})
        tenant = repository.tenant_for_api_key(key)
        if not tenant:
            raise HTTPException(401, detail={"error": "Invalid API key"})
        return tenant

    @app.get("/")
    def home():
        return {"name": "Embeddable Widget & Lead-Capture Platform", "version": "1.0.0", "docs": "/docs", "health": "/health"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/widgets", status_code=201)
    def create_widget(payload: WidgetCreate, tenant=Depends(current_tenant)):
        return _dump_widget(repository.create_widget(tenant["id"], payload.model_dump(mode="json")))

    @app.get("/api/widgets")
    def list_widgets(tenant=Depends(current_tenant)):
        return [_dump_widget(item) for item in repository.list_widgets(tenant["id"])]

    @app.get("/api/widgets/{widget_id}")
    def get_widget(widget_id: UUID, tenant=Depends(current_tenant)):
        widget = repository.get_widget(tenant["id"], widget_id)
        if not widget:
            raise HTTPException(404, detail={"error": "Widget not found"})
        return _dump_widget(widget)

    @app.put("/api/widgets/{widget_id}")
    def update_widget(widget_id: UUID, payload: WidgetUpdate, tenant=Depends(current_tenant)):
        widget = repository.update_widget(tenant["id"], widget_id, payload.model_dump(mode="json"))
        if not widget:
            raise HTTPException(404, detail={"error": "Widget not found"})
        return _dump_widget(widget)

    @app.delete("/api/widgets/{widget_id}", status_code=204)
    def delete_widget(widget_id: UUID, tenant=Depends(current_tenant)):
        if not repository.delete_widget(tenant["id"], widget_id):
            raise HTTPException(404, detail={"error": "Widget not found"})
        return Response(status_code=204)

    @app.get("/api/widgets/{widget_id}/snippet")
    def widget_snippet(widget_id: UUID, tenant=Depends(current_tenant)):
        if not repository.get_widget(tenant["id"], widget_id):
            raise HTTPException(404, detail={"error": "Widget not found"})
        snippet = f'<script async src="{settings.public_base_url}/assets/widget.v1.js?id={widget_id}"></script>'
        return {"widget_id": str(widget_id), "snippet": snippet}

    @app.get("/widgets/{widget_id}/config")
    def public_widget_config(widget_id: UUID, response: Response):
        widget = repository.get_public_widget(widget_id)
        if not widget:
            raise HTTPException(404, detail={"error": "Widget not found"})
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
        return {"id": str(widget["id"]), "type": widget["type"], "title": widget["title"], "description": widget["description"], "fields": widget["form_fields"], "button_text": widget["button_text"], "display_options": widget["display_options"], "submit_url": f"{settings.public_base_url}/submissions"}

    @app.get("/assets/widget.v1.js", response_class=PlainTextResponse)
    def widget_bundle():
        return PlainTextResponse(WIDGET_BUNDLE.read_text(encoding="utf-8"), media_type="application/javascript", headers={"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"})

    @app.post("/submissions", status_code=201)
    def create_submission(payload: SubmissionCreate, request: Request, response: Response, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128)):
        widget = repository.get_public_widget(payload.widget_id)
        if not widget:
            raise HTTPException(404, detail={"error": "Widget not found"})
        if payload.website:
            response.status_code = 202
            return {"accepted": True}
        if idempotency_key:
            existing = repository.find_submission_by_idempotency(payload.widget_id, idempotency_key)
            if existing:
                response.status_code = 200
                response.headers["X-Idempotent-Replay"] = "true"
                return {"id": str(existing["id"]), "accepted": True, "replayed": True}
        forwarded_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() if settings.trust_proxy_headers else ""
        ip = forwarded_ip or (request.client.host if request.client else "127.0.0.1")
        try:
            rate_limiter.check(ip, str(payload.widget_id))
        except RateLimitExceeded as exc:
            raise HTTPException(429, detail={"error": "Rate limit exceeded"}, headers={"Retry-After": str(exc.retry_after)}) from exc
        cleaned = validate_submission_data(widget, payload)
        geo = geo_enricher.enrich(ip)
        submission, created = repository.create_submission_with_job(widget=widget, data=cleaned, ip_address=ip, geo=geo, idempotency_key=idempotency_key)
        if not created:
            response.status_code = 200
            response.headers["X-Idempotent-Replay"] = "true"
        return {"id": str(submission["id"]), "accepted": True, "replayed": not created}

    @app.get("/api/submissions")
    def list_submissions(limit: int = Query(default=100, ge=1, le=500), tenant=Depends(current_tenant)):
        return [jsonable_row(item) for item in repository.list_submissions(tenant["id"], limit)]

    @app.get("/api/dashboard/stats")
    def dashboard_stats(tenant=Depends(current_tenant)):
        stats = repository.dashboard_stats(tenant["id"])
        return {"total": stats["total"], "per_widget": [jsonable_row(row) for row in stats["per_widget"]], "over_time": [jsonable_row(row) for row in stats["over_time"]], "geo": [jsonable_row(row) for row in stats["geo"]]}

    return app
