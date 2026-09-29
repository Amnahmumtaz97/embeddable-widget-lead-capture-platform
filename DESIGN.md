# Design: embeddable widget and lead-capture platform

## Problem and boundaries

Customers need to define a small lead form, embed it on a site they do not share with the API, and inspect safely captured leads. The public path is hostile by default: payloads are bounded and validated, spam is filtered, traffic is rate-limited, and optional upstream work degrades without losing the lead.

The explicit non-goal is a general-purpose visual form builder or production CDN. The UI proves the embed and dashboard flows; backend correctness is the product.

## Data model

- `tenants`: owner identity and SHA-256 API-key hash; raw keys are never stored.
- `widgets`: tenant-owned configuration, JSON form schema, presentation options, and active state. Indexed by tenant.
- `submissions`: tenant and widget ownership copied onto each lead, validated JSON data, IP and optional geo fields. Indexed for dashboard queries. A partial unique index provides per-widget idempotency.
- `side_effect_jobs`: durable transactional outbox for notifications, with attempts, exponential retry scheduling, terminal status, and an alert log.
- `ai_usage`: attribution and per-call token/cost fields if an AI feature is ever enabled. No runtime AI feature exists today, and the configured budget defaults to zero.

## Request paths and layers

```text
Owner + API key -> HTTP routes -> widget/dashboard services -> tenant-scoped repository -> Supabase database
Customer page -> versioned widget.v1.js -> cached public config -> Shadow DOM form
Visitor -> CORS/preflight -> size + schema validation -> rate/spam controls
        -> geo A -> geo B -> store lead + outbox job atomically -> success
Worker -> claim outbox job -> notify -> complete OR retry -> terminal alert
```

HTTP concerns live in `app/api.py`, business rules in `app/services/`, and SQL/persistence in `app/repositories.py`. Every owner query requires a tenant ID. Public submission discovers the tenant only from the selected active widget.

## API contracts

Authenticated routes accept `X-API-Key` or `Authorization: Bearer <key>`. Widget CRUD lives under `/api/widgets`; `/api/submissions` and `/api/dashboard/stats` are owner-only. Public delivery uses `GET /assets/widget.v1.js`, `GET /widgets/{id}/config`, and `POST /submissions`. Errors are JSON with an `error` key and appropriate 4xx status.

## Failure policy

Provider A failure falls through to provider B; both failing produces a lead without geo. Submission storage and job enqueue share one transaction. Notifications run after the response, retry three times with backoff, and emit an `ALERT` log if exhausted. An `Idempotency-Key` retry returns the original lead and creates no duplicate job.
