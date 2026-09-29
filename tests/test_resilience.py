import httpx
import pytest

from app.config import Settings
from app.repositories import SupabaseRepository
from app.services.geo import GeoEnricher
from app.services.jobs import ConsoleNotifier, JobWorker
from tests.conftest import WIDGET_PAYLOAD


def test_geo_provider_fallback_and_total_failure():
    def fallback_handler(request):
        if request.url.host == "provider-a.test":
            return httpx.Response(503)
        return httpx.Response(200, json={"country_name": "Pakistan", "country_code": "PK", "city": "Karachi"})
    settings = Settings(geo_provider_a_url="https://provider-a.test/{ip}", geo_provider_b_url="https://provider-b.test/{ip}")
    enricher = GeoEnricher(settings, httpx.Client(transport=httpx.MockTransport(fallback_handler)))
    assert enricher.enrich("203.0.113.4")["provider"] == "provider_b"
    down = GeoEnricher(settings, httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503))))
    assert down.enrich("203.0.113.4") is None


def test_notification_failure_retries_without_losing_submission(app_factory):
    client, repo = app_factory()
    widget = client.post("/api/widgets", headers={"X-API-Key": "key-a"}, json=WIDGET_PAYLOAD).json()
    response = client.post("/submissions", json={"widget_id": widget["id"], "data": {"email": "a@example.com", "message": "saved"}})
    assert response.status_code == 201 and len(repo.submissions) == 1
    worker = JobWorker(repo, ConsoleNotifier(force_failure=True), Settings(worker_enabled=False))
    assert worker.process_once() == 1
    assert len(repo.submissions) == 1 and repo.jobs[0]["status"] == "retry"


def test_supabase_configuration_prefers_explicit_supabase_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://legacy.example/postgres")
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "postgresql://pooler.supabase.com/postgres")
    assert Settings.from_env().database_url == "postgresql://pooler.supabase.com/postgres"


def test_supabase_repository_requires_configuration_and_tls(monkeypatch):
    with pytest.raises(RuntimeError, match="SUPABASE_DATABASE_URL is required"):
        SupabaseRepository("").connect()
    captured = {}
    marker = object()
    def fake_connect(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return marker
    monkeypatch.setattr("app.repositories.psycopg.connect", fake_connect)
    assert SupabaseRepository("postgresql://pooler.supabase.com/postgres").connect() is marker
    assert captured["sslmode"] == "require"
