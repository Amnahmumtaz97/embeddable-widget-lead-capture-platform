# Embeddable Widget & Lead-Capture Platform

A multi-tenant FastAPI/PostgreSQL platform that lets an owner define a lead widget and embed it on any website with one versioned `<script>` tag. Public submissions are size-bounded, schema-validated, CORS-enabled, rate-limited, spam-filtered, geo-enriched through a fallback chain, stored idempotently, and followed by a retryable background notification. Owners get tenant-isolated CRUD, lead listings, and aggregate statistics.

## Architecture

```text
Widget owner (authenticated API key)
  -> /api/widgets CRUD -----------------------> PostgreSQL widgets (tenant scoped)
  -> /api/submissions + /api/dashboard/stats -> PostgreSQL leads + aggregates

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

The code is layered: HTTP contracts and middleware are in `app/api.py`, business rules are in `app/services/`, persistence and tenant-scoped SQL are in `app/repositories.py`, and schema history is in `migrations/`.

## Run and seed

Requirements: Docker with Compose. No paid account, API key, or credit card is needed.

```bash
cp .env.example .env
docker compose up --build
```

In another terminal, seed two demo tenants and the widget used by the test page:

```bash
docker compose exec app python seed.py
```

Then open:

- API/OpenAPI: `http://localhost:8000/docs`
- second-origin widget demo: `http://localhost:5500`
- simple owner dashboard: `http://localhost:5500/dashboard.html`

The committed placeholder demo key is `demo-tenant-a-key` only when `.env` is absent. If you copied `.env.example`, use the `DEMO_TENANT_A_API_KEY` value you set there. Use long random keys outside local demonstration.

Run the deterministic acceptance suite:

```bash
docker compose exec app pytest -q
```

To prove provider fallback manually, point `GEO_PROVIDER_A_URL` and `GEO_PROVIDER_B_URL` at local mock endpoints. Toggle either provider with `GEO_PROVIDER_A_ENABLED` / `GEO_PROVIDER_B_ENABLED`. Set `NOTIFICATION_FORCE_FAILURE=true` to prove that a stored submission survives notification retries. Automated proofs use mock transports and require no network.

## Authentication and tenancy

Owner endpoints require either:

```http
X-API-Key: demo-tenant-a-key
```

or `Authorization: Bearer demo-tenant-a-key`. Only SHA-256 hashes are stored. Every owner repository query includes `tenant_id`; another tenant receives `404` instead of learning whether a resource exists.

## API

| Method | Path | Auth | Purpose |
|---|---|---:|---|
| GET | `/health` | No | Health probe |
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

Versioned SQL migrations create indexed PostgreSQL tables. A submission and its notification job are committed atomically. The worker uses `FOR UPDATE SKIP LOCKED`, exponential retry scheduling, and a terminal alert. A partial unique index on `(widget_id, idempotency_key)` guarantees a retried lead is stored once, even under concurrent requests.

The product makes no AI calls, so runtime AI cost is $0. `AI_MONTHLY_BUDGET_USD` defaults to `0`, and an `ai_usage` table is ready for per-call attribution before any future AI feature is enabled.

## Limitations

- Rate-limit state is in one application process. A multi-replica deployment should move counters to Redis or another shared store.
- The included side effect logs a notification rather than sending real email; this keeps the project free and makes failure behavior deterministic.
- Geo services are external best-effort dependencies. Private/test IPs often produce no geo, which is an accepted degraded result.
- CORS defaults to `*` for embeddability. Restrict `ALLOWED_ORIGINS` for a product with an owner-configured allowlist.
- The demo dashboard intentionally stores its API key only in the current page DOM; it is proof, not a production frontend.

See `DESIGN.md` for the design contract, `EVIDENCE.md` for requirement-by-requirement proof, and `BUILDLOG.md` for the AI assistance record.
