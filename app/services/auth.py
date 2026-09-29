from typing import Any

import httpx


class AuthConfigurationError(RuntimeError):
    pass


class AuthProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class SupabaseAuthService:
    """Small server-side client for Supabase Auth's GoTrue HTTP API."""

    def __init__(
        self,
        project_url: str,
        publishable_key: str,
        *,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ):
        self.project_url = project_url.rstrip("/")
        self.publishable_key = publishable_key
        self.client = client or httpx.Client(timeout=timeout_seconds)

    @property
    def configured(self) -> bool:
        return bool(self.project_url and self.publishable_key)

    def _headers(self, token: str | None = None) -> dict[str, str]:
        if not self.configured:
            raise AuthConfigurationError(
                "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY are required"
            )
        headers = {"apikey": self.publishable_key, "Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return "Authentication provider request failed"
        return str(
            payload.get("msg")
            or payload.get("message")
            or payload.get("error_description")
            or payload.get("error")
            or "Authentication provider request failed"
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self.client.request(
                method,
                f"{self.project_url}/auth/v1{path}",
                headers=self._headers(token),
                json=json,
            )
        except httpx.HTTPError as exc:
            raise AuthProviderError("Authentication provider unavailable", 503) from exc
        if response.status_code >= 400:
            raise AuthProviderError(self._error_message(response), response.status_code)
        if response.status_code == 204 or not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise AuthProviderError("Authentication provider returned invalid JSON", 502) from exc

    def signup(self, email: str, password: str) -> dict[str, Any]:
        return self._request("POST", "/signup", json={"email": email, "password": password})

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/token?grant_type=password",
            json={"email": email, "password": password},
        )

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/token?grant_type=refresh_token",
            json={"refresh_token": refresh_token},
        )

    def verify(self, token: str) -> dict[str, Any]:
        return self._request("GET", "/user", token=token)

    def logout(self, token: str) -> None:
        self._request("POST", "/logout", token=token, json={})
