from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BASE_DIR / "migrations"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


class PostgresRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def migrate(self) -> None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations "
                    "(version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
                )
                for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                    cursor.execute("SELECT 1 FROM schema_migrations WHERE version = %s", (path.name,))
                    if cursor.fetchone() is None:
                        cursor.execute(path.read_text(encoding="utf-8"))
                        cursor.execute("INSERT INTO schema_migrations(version) VALUES (%s)", (path.name,))

    def seed_demo(self, tenant_a_key: str, tenant_b_key: str) -> None:
        tenants = [
            ("11111111-1111-1111-1111-111111111111", "Demo Tenant A", hash_api_key(tenant_a_key)),
            ("22222222-2222-2222-2222-222222222222", "Demo Tenant B", hash_api_key(tenant_b_key)),
        ]
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO tenants(id, name, api_key_hash) VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, api_key_hash = EXCLUDED.api_key_hash""",
                    tenants,
                )
                cursor.execute(
                    """INSERT INTO widgets(id, tenant_id, type, title, description, form_fields, button_text, display_options)
                    VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', %s, 'contact', 'Request a callback',
                    'Leave your details and our team will follow up.', %s, 'Send request', %s)
                    ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title, description=EXCLUDED.description,
                    form_fields=EXCLUDED.form_fields, button_text=EXCLUDED.button_text, display_options=EXCLUDED.display_options""",
                    (
                        tenants[0][0],
                        Jsonb([
                            {"name": "name", "label": "Name", "type": "text", "required": True, "max_length": 100},
                            {"name": "email", "label": "Email", "type": "email", "required": True, "max_length": 120},
                        ]),
                        Jsonb({"theme": "light"}),
                    ),
                )

    def tenant_for_api_key(self, api_key: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, name FROM tenants WHERE api_key_hash = %s",
                    (hash_api_key(api_key),),
                )
                return cursor.fetchone()

    def create_widget(self, tenant_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO widgets
                    (tenant_id, type, title, description, form_fields, button_text, display_options)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        tenant_id,
                        payload["type"],
                        payload["title"],
                        payload["description"],
                        Jsonb(payload["fields"]),
                        payload["button_text"],
                        Jsonb(payload["display_options"]),
                    ),
                )
                return cursor.fetchone()

    def list_widgets(self, tenant_id: UUID | str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM widgets WHERE tenant_id = %s ORDER BY created_at DESC", (tenant_id,))
                return cursor.fetchall()

    def get_widget(self, tenant_id: UUID | str, widget_id: UUID | str) -> dict[str, Any] | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM widgets WHERE id = %s AND tenant_id = %s", (widget_id, tenant_id))
                return cursor.fetchone()

    def get_public_widget(self, widget_id: UUID | str) -> dict[str, Any] | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM widgets WHERE id = %s AND active = TRUE", (widget_id,))
                return cursor.fetchone()

    def update_widget(self, tenant_id: UUID | str, widget_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any] | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE widgets SET type=%s, title=%s, description=%s, form_fields=%s,
                    button_text=%s, display_options=%s, updated_at=NOW()
                    WHERE id=%s AND tenant_id=%s RETURNING *""",
                    (
                        payload["type"], payload["title"], payload["description"], Jsonb(payload["fields"]),
                        payload["button_text"], Jsonb(payload["display_options"]), widget_id, tenant_id,
                    ),
                )
                return cursor.fetchone()

    def delete_widget(self, tenant_id: UUID | str, widget_id: UUID | str) -> bool:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM widgets WHERE id=%s AND tenant_id=%s", (widget_id, tenant_id))
                return cursor.rowcount > 0

    def find_submission_by_idempotency(self, widget_id: UUID | str, key: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM submissions WHERE widget_id=%s AND idempotency_key=%s",
                    (widget_id, key),
                )
                return cursor.fetchone()

    def create_submission_with_job(
        self,
        *,
        widget: dict[str, Any],
        data: dict[str, str],
        ip_address: str,
        geo: dict[str, Any] | None,
        idempotency_key: str | None,
    ) -> tuple[dict[str, Any], bool]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO submissions
                    (tenant_id, widget_id, data, ip_address, country, country_code, city, geo_provider, idempotency_key)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (widget_id, idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
                    RETURNING *""",
                    (
                        widget["tenant_id"], widget["id"], Jsonb(data), ip_address,
                        geo.get("country") if geo else None, geo.get("country_code") if geo else None,
                        geo.get("city") if geo else None, geo.get("provider") if geo else None,
                        idempotency_key,
                    ),
                )
                row = cursor.fetchone()
                created = row is not None
                if not created:
                    cursor.execute(
                        "SELECT * FROM submissions WHERE widget_id=%s AND idempotency_key=%s",
                        (widget["id"], idempotency_key),
                    )
                    row = cursor.fetchone()
                else:
                    cursor.execute(
                        "INSERT INTO side_effect_jobs(tenant_id, submission_id, kind, payload) VALUES (%s,%s,'console_notification',%s)",
                        (widget["tenant_id"], row["id"], Jsonb({"widget_id": str(widget["id"]), "submission_id": str(row["id"])})),
                    )
                return row, created

    def list_submissions(self, tenant_id: UUID | str, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT s.*, w.title AS widget_title FROM submissions s
                    JOIN widgets w ON w.id=s.widget_id
                    WHERE s.tenant_id=%s ORDER BY s.created_at DESC LIMIT %s""",
                    (tenant_id, limit),
                )
                return cursor.fetchall()

    def dashboard_stats(self, tenant_id: UUID | str) -> dict[str, Any]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM submissions WHERE tenant_id=%s", (tenant_id,))
                total = cursor.fetchone()["total"]
                cursor.execute(
                    """SELECT w.id AS widget_id, w.title, COUNT(s.id) AS count FROM widgets w
                    LEFT JOIN submissions s ON s.widget_id=w.id AND s.tenant_id=%s
                    WHERE w.tenant_id=%s GROUP BY w.id, w.title ORDER BY count DESC""",
                    (tenant_id, tenant_id),
                )
                per_widget = cursor.fetchall()
                cursor.execute(
                    """SELECT DATE(created_at) AS date, COUNT(*) AS count FROM submissions
                    WHERE tenant_id=%s GROUP BY DATE(created_at) ORDER BY date""",
                    (tenant_id,),
                )
                over_time = cursor.fetchall()
                cursor.execute(
                    """SELECT COALESCE(country, 'Unknown') AS country, COUNT(*) AS count FROM submissions
                    WHERE tenant_id=%s GROUP BY COALESCE(country, 'Unknown') ORDER BY count DESC""",
                    (tenant_id,),
                )
                geo = cursor.fetchall()
        return {"total": total, "per_widget": per_widget, "over_time": over_time, "geo": geo}

    def claim_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """WITH claimed AS (
                        SELECT id FROM side_effect_jobs
                        WHERE status IN ('pending','retry') AND next_attempt_at <= NOW()
                        ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT %s
                    )
                    UPDATE side_effect_jobs j SET status='processing', attempts=attempts+1, updated_at=NOW()
                    FROM claimed WHERE j.id=claimed.id RETURNING j.*""",
                    (limit,),
                )
                return cursor.fetchall()

    def complete_job(self, job_id: UUID | str) -> None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE side_effect_jobs SET status='completed', updated_at=NOW() WHERE id=%s", (job_id,))

    def fail_job(self, job_id: UUID | str, error: str, terminal: bool) -> None:
        status = "failed" if terminal else "retry"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE side_effect_jobs SET status=%s, last_error=%s,
                    next_attempt_at=NOW() + (INTERVAL '1 second' * POWER(2, attempts)), updated_at=NOW()
                    WHERE id=%s""",
                    (status, error[:1_000], job_id),
                )


def jsonable_row(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (UUID, date, datetime)):
            result[key] = value.isoformat() if isinstance(value, (date, datetime)) else str(value)
        else:
            result[key] = value
    return result
