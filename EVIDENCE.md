# Capstone evidence

All proofs are deterministic and run without paid services. The command used was:

```text
> .\.venv\Scripts\python.exe -m pytest -v --disable-warnings
collected 9 items
tests/test_acceptance.py::test_authenticated_crud_and_tenant_isolation PASSED
tests/test_acceptance.py::test_versioned_delivery_cache_snippet_and_cors_preflight PASSED
tests/test_acceptance.py::test_submission_validation_spam_geo_idempotency_and_dashboard PASSED
tests/test_acceptance.py::test_malformed_oversized_and_rate_limited_requests_are_clean_json PASSED
tests/test_acceptance.py::test_invalid_widget_payload_is_rejected PASSED
tests/test_resilience.py::test_geo_provider_fallback_and_total_failure PASSED
tests/test_resilience.py::test_notification_failure_retries_without_losing_submission PASSED
tests/test_resilience.py::test_supabase_configuration_prefers_explicit_supabase_url PASSED
tests/test_resilience.py::test_supabase_repository_requires_configuration_and_tls PASSED
9 passed, 1 warning in 0.36s
```

The warning is Starlette's notice that its `TestClient` compatibility import will move to `httpx2`; it does not affect application behavior.

## Section 6 requirements

- [x] Authenticated widget CRUD; invalid or absent authentication rejected.
  Proof: `test_authenticated_crud_and_tenant_isolation PASSED` exercises unauthenticated `401`, create, read, update, and delete.

- [x] Tenant A cannot read or modify tenant B's widgets or submissions.
  Proof: `test_authenticated_crud_and_tenant_isolation PASSED` receives `404` for cross-tenant widget read/update; `test_submission_validation_spam_geo_idempotency_and_dashboard PASSED` receives an empty tenant-B submission list after tenant A submits.

- [x] Embed snippet generated per widget.
  Proof: `test_versioned_delivery_cache_snippet_and_cors_preflight PASSED` verifies the snippet contains the widget ID and versioned bundle URL.

- [x] Public config is small and has correct cache headers.
  Proof: `test_versioned_delivery_cache_snippet_and_cors_preflight PASSED` verifies `200` and `Cache-Control: public, max-age=60, stale-while-revalidate=300`.

- [x] Widget JavaScript is a versioned bundle.
  Proof: `test_versioned_delivery_cache_snippet_and_cors_preflight PASSED` fetches `/assets/widget.v1.js` and verifies the one-year `immutable` cache policy.

- [x] Widget is wired to a page on a different origin.
  Proof: `test_versioned_delivery_cache_snippet_and_cors_preflight PASSED` verifies the `localhost:5500` demo loads the bundle from `localhost:8000`; the same test fetches its config and completes cross-origin preflight.

- [x] Cross-origin submission and `OPTIONS` preflight work.
  Proof: `test_versioned_delivery_cache_snippet_and_cors_preflight PASSED` sends a browser-form preflight from `http://localhost:5500` and verifies `200` plus `Access-Control-Allow-Origin: *`.

- [x] Malformed and oversized payloads return clean 4xx JSON.
  Proof: `test_malformed_oversized_and_rate_limited_requests_are_clean_json PASSED` verifies malformed JSON returns `422 {"error":"Invalid request",...}` and an over-limit body returns `413 {"error":"Payload too large"}`; `test_invalid_widget_payload_is_rejected PASSED` covers admin-boundary validation.

- [x] Valid submissions are stored against the correct widget and tenant.
  Proof: `test_submission_validation_spam_geo_idempotency_and_dashboard PASSED` stores one lead, observes it in tenant A's dashboard, and proves it is absent for tenant B.

- [x] Per-IP and per-widget burst controls return `429` while service stays healthy.
  Proof: `test_malformed_oversized_and_rate_limited_requests_are_clean_json PASSED` exceeds the IP window, verifies `429` plus `Retry-After`, then verifies `/health` still returns `200`. The same limiter atomically checks an independent widget window.

- [x] Honeypot blocks spam.
  Proof: `test_submission_validation_spam_geo_idempotency_and_dashboard PASSED` fills `website`, receives the intentionally quiet `202`, and verifies zero rows were stored.

- [x] Provider A failure falls back to provider B and enriches the submission.
  Proof: `test_geo_provider_fallback_and_total_failure PASSED` makes A return `503`, makes B return Karachi/Pakistan, and verifies `provider_b`; the submission acceptance test verifies that result is persisted.

- [x] All geo providers may fail without failing submission.
  Proof: `test_geo_provider_fallback_and_total_failure PASSED` makes both providers return `503` and verifies the enrichment result is `None`; the submission path accepts `None` and stores the lead.

- [x] A failing notification does not roll back the lead.
  Proof: `test_notification_failure_retries_without_losing_submission PASSED` forces the notifier to throw, verifies the lead remains stored, and verifies the durable job moves to `retry`.

- [x] README architecture, setup, API documentation, and required files are present.
  Proof:

  ```text
  README.md=True
  capstone.yaml=True
  EVIDENCE.md=True
  BUILDLOG.md=True
  .env.example=True
  LICENSE=True
  DESIGN.md=True
  ```

## Shared capstone requirements

- [x] Layered architecture.
  Proof: `app/api.py` contains HTTP concerns, `app/services/` contains validation/enrichment/limits/jobs, and `app/repositories.py` contains persistence. All modules pass `python -m compileall`.

- [x] Boundary validation.
  Proof: the malformed, oversized, invalid-widget, and dynamic-field acceptance tests above all pass with 4xx responses, never 500.

- [x] At least one retrying background job with failure alert.
  Proof: `test_notification_failure_retries_without_losing_submission PASSED`; `JobWorker` claims durable jobs, applies exponential retry state, and logs `ALERT side_effect_job_exhausted` after the final attempt.

- [x] Real persistence with Supabase migrations, indexes, and isolated tenants.
  Proof: `supabase/migrations/20260929000000_initial.sql` creates Supabase Postgres tables plus tenant/widget/time/ready-job indexes; `SupabaseRepository.create_submission_with_job` writes the lead and outbox job in one database transaction. Every owner query filters `tenant_id`. `test_supabase_repository_requires_configuration_and_tls PASSED` proves missing configuration fails closed and connections require TLS.

- [x] Idempotency where retries matter.
  Proof: `test_submission_validation_spam_geo_idempotency_and_dashboard PASSED` repeats the same `Idempotency-Key`, receives `X-Idempotent-Replay: true`, and verifies exactly one submission. PostgreSQL also enforces a partial unique index.

- [x] Secrets are environment-only and never logged.
  Proof: `.gitignore` excludes `.env`; `.env.example` contains safe placeholders; tenants store only `sha256(api_key)`; job logging contains submission IDs, not credentials.

- [x] AI cost handling.
  Proof: the product makes zero runtime AI calls and therefore costs $0. `AI_MONTHLY_BUDGET_USD` defaults to `0`, and the `ai_usage` table has provider/model/operation/token/cost attribution columns that must be used before a future AI feature is enabled. Development-time AI assistance is disclosed in `BUILDLOG.md`.

## Static checks

```text
> python -m compileall -q app main.py seed.py tests
exit 0
> node --check assets/widget.v1.js
exit 0
> git diff --check
exit 0 (line-ending conversion notices only)
```

## Live Supabase smoke test

Run on 2026-09-29 against the configured Supabase Session pooler after applying migrations and seeding demo data:

```text
ConfigStatus=200
ConfigCache=public, max-age=60, stale-while-revalidate=300
SubmissionAccepted=true
SubmissionReplayed=false
DashboardTotal=1
DemoStatus=200
```

The smoke submission used the stable idempotency key `setup-smoke-20260929`, so rerunning the check cannot create duplicate leads.
