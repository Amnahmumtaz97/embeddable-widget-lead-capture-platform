from typing import Any

import httpx

from app.config import Settings


class GeoEnricher:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self.client = client or httpx.Client(timeout=settings.geo_timeout_seconds)

    def enrich(self, ip: str) -> dict[str, str | None] | None:
        providers = []
        if self.settings.geo_provider_a_enabled:
            providers.append(("provider_a", self.settings.geo_provider_a_url, self._parse_a))
        if self.settings.geo_provider_b_enabled:
            providers.append(("provider_b", self.settings.geo_provider_b_url, self._parse_b))
        for name, template, parser in providers:
            try:
                response = self.client.get(template.format(ip=ip))
                response.raise_for_status()
                parsed = parser(response.json())
                if parsed:
                    return {**parsed, "provider": name}
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                continue
        return None

    @staticmethod
    def _parse_a(payload: dict[str, Any]) -> dict[str, str | None] | None:
        if payload.get("status") not in (None, "success"):
            return None
        country = payload.get("country")
        if not country:
            return None
        return {"country": country, "country_code": payload.get("countryCode"), "city": payload.get("city")}

    @staticmethod
    def _parse_b(payload: dict[str, Any]) -> dict[str, str | None] | None:
        if payload.get("error"):
            return None
        country = payload.get("country_name")
        if not country:
            return None
        return {"country": country, "country_code": payload.get("country_code"), "city": payload.get("city")}


class NullGeoEnricher:
    def enrich(self, ip: str):
        return None
