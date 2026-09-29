# Embeddable Widget & Lead-Capture Platform

A multi-tenant FastAPI/Supabase platform that lets an owner define a lead widget and embed it on any website with one versioned `<script>` tag. Public submissions are size-bounded, schema-validated, CORS-enabled, rate-limited, spam-filtered, geo-enriched through a fallback chain, stored idempotently, and followed by a retryable background notification. Owners get tenant-isolated CRUD, lead listings, and aggregate statistics.

## Architecture

```text
Widget owner (authenticated API key)
  -> /api/widgets CRUD -----------------------> Supabase widgets (tenant scoped)
  -> /api/submissions + /api/dashboard/stats -> Supabase leads + aggregates

Customer site :5500
  -> cached /assets/widget.v1.js?id=...
  -> cached /widgets/{id}/config
  -> renders isolated form in Shadow DOM

Visitor (public, any origin)
  -> OPTIONS /submissions (CORS preflight)
  -> POST /submissions
       payload bound -> Pydantic + dynamic form validation
       -> IP/widget rate limit -> honeypot
       -> geo provider A -> provider B -> no geo (all are valid outcomes)
       -> one transaction: lead + durable notification job
       -> 2xx immediately

Background worker
  -> claims jobs safely -> console notification
  -> exponential retries -> terminal ALERT log
```

The code is layered: HTTP contracts and middleware are in `app/api.py`, business rules are in `app/services/`, persistence and tenant-scoped SQL are in `app/repositories.py`, and schema history is in `supabase/migrations/`.

## Run and seed

Requirements: a free Supabase project and Docker with Compose. The API connects directly to Supabase's managed Postgres database; the browser never receives the database password or a service-role key.

1. Create a Supabase project.
2. In its dashboard, select **Connect**, choose **Session pooler**, and copy the connection string. Session mode uses port `5432` and works from IPv4-only networks.
3. Copy the environment template and replace `URL_ENCODED_PASSWORD` in `SUPABASE_DATABASE_URL` with the project's database password. If this repository already has a `.env` from the old local database, replace its `POSTGRES_*` / `DATABASE_URL` entries with `SUPABASE_DATABASE_URL`. Percent-encode reserved password characters and retain `sslmode=require`.

```bash
cp .env.example .env
```

4. Start the API and second-origin demo. The API applies `supabase/migrations/20260929000000_initial.sql` automatically over a TLS-required connection.

```bash
docker compose up --build
```

5. In another terminal, seed two demo tenants and the widget used by the test page:

```bash
docker compose exec app python seed.py
```

Then open:

- API/OpenAPI: `http://localhost:8000/docs`
- second-origin widget demo: `http://localhost:5500`
- simple owner dashboard: `http://localhost:5500/dashboard.html`

The local demo key is `demo-tenant-a-key`. Change `DEMO_TENANT_A_API_KEY` and `DEMO_TENANT_B_API_KEY` to long random values outside local demonstration, then enter the chosen tenant-A key on the dashboard page.

Run the deterministic acceptance suite:

```bash
docker compose exec app pytest -q
```

To prove provider fallback manually, point `GEO_PROVIDER_A_URL` and `GEO_PROVIDER_B_URL` at local mock endpoints. Toggle either provider with `GEO_PROVIDER_A_ENABLED` / `GEO_PROVIDER_B_ENABLED`. Set `NOTIFICATION_FORCE_FAILURE=true` to prove that a stored submission survives notification retries. Automated proofs use mock transports and require no network.

## Authentication and tenancy

The project now supports two separate authentication concerns:

- Supabase Auth handles end-user signup, login, refresh, verified JWT access, and logout.
- Tenant API keys continue to protect owner widget-management and analytics routes.

Supabase Auth uses the existing environment names from `.env.example`: `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`. The publishable key is sent only to Supabase Auth; the database connection string remains server-side. Swagger UI at `/docs` exposes a Bearer JWT authorization scheme and lock icons on protected routes.

End-user flow:

```text
POST /auth/signup -> POST /auth/login -> copy access_token
-> Swagger Authorize: Bearer <access_token>
-> GET /protected/profile -> POST /auth/logout
```

Owner endpoints require either:

```http
X-API-Key: demo-tenant-a-key
```

or `Authorization: Bearer demo-tenant-a-key`. Only SHA-256 hashes are stored. Every owner repository query includes `tenant_id`; another tenant receives `404` instead of learning whether a resource exists.

## API

| Method | Path | Auth | Purpose |
|---|---|---:|---|
| GET | `/health` | No | Health probe |
| GET | `/public/info` | No | Public authentication example |
| POST | `/auth/signup` | No | Create a Supabase Auth user |
| POST | `/auth/login` | No | Return access and refresh tokens |
| POST | `/auth/refresh` | Refresh token | Rotate an expired access token |
| POST | `/auth/logout` | Bearer JWT | End the Supabase Auth session |
| GET | `/protected/profile` | Bearer JWT | Return safe verified user metadata |
| GET | `/protected/dashboard` | Bearer JWT | Prove reusable route protection |
| POST | `/api/widgets` | Yes | Create validated widget |
| GET | `/api/widgets` | Yes | List the tenant's widgets |
| GET | `/api/widgets/{id}` | Yes | Read one tenant widget |
| PUT | `/api/widgets/{id}` | Yes | Replace one tenant widget |
| DELETE | `/api/widgets/{id}` | Yes | Delete one tenant widget |
| GET | `/api/widgets/{id}/snippet` | Yes | Generate the one-line embed |
| GET | `/assets/widget.v1.js` | No | Long-cache immutable bundle |
| GET | `/widgets/{id}/config` | No | Short-cache public config |
| POST | `/submissions` | No | Hardened public lead capture |
| GET | `/api/submissions` | Yes | Tenant-isolated lead table data |
| GET | `/api/dashboard/stats` | Yes | Counts over time, by widget, and by country |

Create a widget:

```bash
curl -X POST http://localhost:8000/api/widgets \
  -H "X-API-Key: demo-tenant-a-key" \
  -H "Content-Type: application/json" \
  -d '{"type":"contact","title":"Talk to us","description":"We reply quickly.","fields":[{"name":"email","label":"Email","type":"email","required":true,"max_length":120}],"button_text":"Send","display_options":{"theme":"light"}}'
```

Submit a lead (replace the widget ID if you did not use the seed):

```bash
curl -i -X POST http://localhost:8000/submissions \
  -H "Origin: http://localhost:5500" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-lead-001" \
  -d '{"widget_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","data":{"name":"Ada","email":"ada@example.com"},"website":""}'
```

All errors are JSON. Boundary failures use `401`, `404`, `413`, `422`, or `429` as appropriate. A filled `website` honeypot returns an intentionally non-revealing `202` and stores nothing. Reusing `Idempotency-Key` returns the original submission with `X-Idempotent-Replay: true`.

## Caching, CORS, and proxy safety

The versioned JavaScript bundle sends `Cache-Control: public, max-age=31536000, immutable`; changing the bundle requires a new filename such as `widget.v2.js`. Config sends `public, max-age=60, stale-while-revalidate=300`. CORS handles browser preflight and permits the headers used by the loader.

`X-Forwarded-For` is ignored by default because clients can spoof it. Enable `TRUST_PROXY_HEADERS=true` only behind a trusted reverse proxy that overwrites that header.

## Persistence, jobs, idempotency, and cost

Versioned SQL migrations create indexed tables in Supabase's managed Postgres database. A submission and its notification job are committed atomically. The worker uses `FOR UPDATE SKIP LOCKED`, exponential retry scheduling, and a terminal alert. A partial unique index on `(widget_id, idempotency_key)` guarantees a retried lead is stored once, even under concurrent requests.

The product makes no AI calls, so runtime AI cost is $0. `AI_MONTHLY_BUDGET_USD` defaults to `0`, and an `ai_usage` table is ready for per-call attribution before any future AI feature is enabled.

## Limitations

- Rate-limit state is in one application process. A multi-replica deployment should move counters to Redis or another shared store.
- The included side effect logs a notification rather than sending real email; this keeps the project free and makes failure behavior deterministic.
- Geo services are external best-effort dependencies. Private/test IPs often produce no geo, which is an accepted degraded result.
- CORS defaults to `*` for embeddability. Restrict `ALLOWED_ORIGINS` for a product with an owner-configured allowlist.
- The demo dashboard intentionally stores its API key only in the current page DOM; it is proof, not a production frontend.
- The backend uses Supabase as managed Postgres rather than exposing the Supabase Data API. This preserves transactions, `FOR UPDATE SKIP LOCKED`, and existing SQL indexes while keeping database credentials server-side.

See `DESIGN.md` for the design contract, `EVIDENCE.md` for requirement-by-requirement proof, and `BUILDLOG.md` for the AI assistance record.

## Polite scraper module

The isolated `scraper/` module implements the Books to Scrape assignment without mixing crawler concerns into the API. It processes exactly three catalogue pages, discovers 60 unique detail URLs, uses a named user-agent, a timeout, a minimum 500 ms delay, status checks, cache-first development, bounded retries, Pydantic validation, canonical-URL deduplication, per-page failure isolation, and an honest run report.

```bash
python -m scraper.src.main
python -m scraper.src.main --inject-broken-url
pytest -q scraper/tests
```

See `scraper/README.md` for target classification, ethics, schema, outputs, and limitations. Cached HTML is ignored by Git; validated JSON evidence remains under `scraper/output/`.
