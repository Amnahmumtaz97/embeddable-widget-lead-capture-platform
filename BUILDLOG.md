# Build log

## 2026-09-29 - capstone implementation

AI assistance was used to extract and organize the capstone requirements, draft the FastAPI/PostgreSQL implementation, create deterministic tests, and review the submission pack for omissions.

The initial repository was a todo CRUD API, so the implementation was redesigned around the three actors in the brief: widget owner, customer site, and visitor. Human-owned decisions include using hashed API keys, a durable PostgreSQL outbox instead of an in-request notification, fixed-window-free sliding rate limits, a Shadow DOM widget, and a deliberately small UI.

Corrections made during review included converting an existing UTF-16 requirements file before patching, avoiding trust of `X-Forwarded-For` unless explicitly configured, making validation errors JSON-safe, and adding date serialization for aggregation results. The test output pasted into `EVIDENCE.md` is produced after these corrections.

There are no runtime AI calls in the product. The `ai_usage` schema and zero-dollar budget setting make cost attribution and a default-deny budget available if AI is added later; today runtime AI cost is exactly $0.
