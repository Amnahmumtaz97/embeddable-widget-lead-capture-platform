from functools import lru_cache
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    database_url: str = ""
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    auth_timeout_seconds: float = 5.0
    public_base_url: str = "http://localhost:8000"
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    max_payload_bytes: int = 16_384
    rate_limit_ip: int = 20
    rate_limit_widget: int = 100
    rate_limit_window_seconds: int = 60
    geo_provider_a_url: str = "http://ip-api.com/json/{ip}?fields=status,country,countryCode,city"
    geo_provider_b_url: str = "https://ipapi.co/{ip}/json/"
    geo_provider_a_enabled: bool = True
    geo_provider_b_enabled: bool = True
    geo_timeout_seconds: float = 1.5
    worker_enabled: bool = True
    worker_poll_seconds: float = 2.0
    notification_force_failure: bool = False
    trust_proxy_headers: bool = False
    ai_monthly_budget_usd: float = 0.0

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.getenv("ALLOWED_ORIGINS", "*")
        return cls(
            database_url=os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL", ""),
            supabase_url=os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/"),
            supabase_publishable_key=os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", ""),
            auth_timeout_seconds=float(os.getenv("AUTH_TIMEOUT_SECONDS", "5")),
            public_base_url=os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/"),
            allowed_origins=[item.strip() for item in origins.split(",") if item.strip()],
            max_payload_bytes=int(os.getenv("MAX_PAYLOAD_BYTES", "16384")),
            rate_limit_ip=int(os.getenv("RATE_LIMIT_IP", "20")),
            rate_limit_widget=int(os.getenv("RATE_LIMIT_WIDGET", "100")),
            rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
            geo_provider_a_url=os.getenv("GEO_PROVIDER_A_URL", cls.model_fields["geo_provider_a_url"].default),
            geo_provider_b_url=os.getenv("GEO_PROVIDER_B_URL", cls.model_fields["geo_provider_b_url"].default),
            geo_provider_a_enabled=os.getenv("GEO_PROVIDER_A_ENABLED", "true").lower() == "true",
            geo_provider_b_enabled=os.getenv("GEO_PROVIDER_B_ENABLED", "true").lower() == "true",
            geo_timeout_seconds=float(os.getenv("GEO_TIMEOUT_SECONDS", "1.5")),
            worker_enabled=os.getenv("WORKER_ENABLED", "true").lower() == "true",
            worker_poll_seconds=float(os.getenv("WORKER_POLL_SECONDS", "2")),
            notification_force_failure=os.getenv("NOTIFICATION_FORCE_FAILURE", "false").lower() == "true",
            trust_proxy_headers=os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true",
            ai_monthly_budget_usd=float(os.getenv("AI_MONTHLY_BUDGET_USD", "0")),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
