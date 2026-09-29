import json
from pathlib import Path

from tests.conftest import WIDGET_PAYLOAD


def create_widget(client, key="key-a"):
    response = client.post("/api/widgets", headers={"X-API-Key": key}, json=WIDGET_PAYLOAD)
    assert response.status_code == 201
    return response.json()


def test_authenticated_crud_and_tenant_isolation(app_factory):
    client, _ = app_factory()
    assert client.get("/api/widgets").status_code == 401
    widget = create_widget(client)
    assert client.get(f"/api/widgets/{widget['id']}", headers={"X-API-Key": "key-b"}).status_code == 404
    changed = {**WIDGET_PAYLOAD, "title": "Updated title"}
    assert client.put(f"/api/widgets/{widget['id']}", headers={"X-API-Key": "key-b"}, json=changed).status_code == 404
    assert client.put(f"/api/widgets/{widget['id']}", headers={"X-API-Key": "key-a"}, json=changed).json()["title"] == "Updated title"
    assert client.delete(f"/api/widgets/{widget['id']}", headers={"X-API-Key": "key-a"}).status_code == 204


def test_versioned_delivery_cache_snippet_and_cors_preflight(app_factory):
    client, _ = app_factory()
    widget = create_widget(client)
    snippet = client.get(f"/api/widgets/{widget['id']}/snippet", headers={"X-API-Key": "key-a"}).json()["snippet"]
    assert "widget.v1.js" in snippet and widget["id"] in snippet
    config = client.get(f"/widgets/{widget['id']}/config", headers={"Origin": "http://localhost:5500"})
    assert config.status_code == 200
    assert "max-age=60" in config.headers["cache-control"]
    bundle = client.get("/assets/widget.v1.js")
    assert "immutable" in bundle.headers["cache-control"]
    preflight = client.options("/submissions", headers={"Origin": "http://localhost:5500", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,idempotency-key"})
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "*"
    demo_page = (Path(__file__).parent.parent / "test-site" / "index.html").read_text(encoding="utf-8")
    assert "localhost:5500" in demo_page and "http://localhost:8000/assets/widget.v1.js" in demo_page


def test_submission_validation_spam_geo_idempotency_and_dashboard(app_factory):
    client, repo = app_factory()
    widget = create_widget(client)
    endpoint = "/submissions"
    assert client.post(endpoint, json={"widget_id": widget["id"], "data": {"email": "bad", "message": "hello"}}).status_code == 422
    spam = client.post(endpoint, json={"widget_id": widget["id"], "data": {"email": "a@example.com", "message": "hello"}, "website": "spam.example"})
    assert spam.status_code == 202 and repo.submissions == []
    body = {"widget_id": widget["id"], "data": {"email": "a@example.com", "message": "hello"}}
    first = client.post(endpoint, headers={"Idempotency-Key": "lead-123", "X-Forwarded-For": "203.0.113.4"}, json=body)
    replay = client.post(endpoint, headers={"Idempotency-Key": "lead-123", "X-Forwarded-For": "203.0.113.4"}, json=body)
    assert first.status_code == 201
    assert replay.status_code == 200 and replay.headers["x-idempotent-replay"] == "true"
    assert len(repo.submissions) == 1 and repo.submissions[0]["geo_provider"] == "provider_b"
    assert client.get("/api/submissions", headers={"X-API-Key": "key-b"}).json() == []
    assert client.get("/api/dashboard/stats", headers={"X-API-Key": "key-a"}).json()["total"] == 1


def test_malformed_oversized_and_rate_limited_requests_are_clean_json(app_factory):
    client, _ = app_factory(ip_limit=1, widget_limit=10, max_payload=700)
    widget = create_widget(client)
    malformed = client.post("/submissions", content="{broken", headers={"Content-Type": "application/json"})
    assert malformed.status_code == 422 and malformed.json()["error"] == "Invalid request"
    oversized = client.post("/submissions", content=json.dumps({"padding": "x" * 1_000}), headers={"Content-Type": "application/json"})
    assert oversized.status_code == 413 and oversized.json() == {"error": "Payload too large"}
    body = {"widget_id": widget["id"], "data": {"email": "a@example.com", "message": "first"}}
    assert client.post("/submissions", json=body, headers={"X-Forwarded-For": "198.51.100.1"}).status_code == 201
    limited = client.post("/submissions", json=body, headers={"X-Forwarded-For": "198.51.100.1"})
    assert limited.status_code == 429 and limited.headers["retry-after"]
    assert client.get("/health").status_code == 200


def test_invalid_widget_payload_is_rejected(app_factory):
    client, _ = app_factory()
    invalid = {**WIDGET_PAYLOAD, "fields": [{"name": "Bad Name", "label": "Bad"}]}
    response = client.post("/api/widgets", headers={"X-API-Key": "key-a"}, json=invalid)
    assert response.status_code == 422
