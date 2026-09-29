from tests.conftest import FakeAuth


def test_public_signup_login_and_input_errors(app_factory):
    client, _ = app_factory()
    assert client.get("/public/info").status_code == 200
    assert client.post("/auth/signup", json={"email": "test@example.com"}).status_code == 400

    signup = client.post(
        "/auth/signup",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert signup.status_code == 201
    assert signup.json()["user"]["email"] == "test@example.com"

    rejected = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert rejected.status_code == 401
    assert rejected.json() == {"error": "Invalid login credentials"}

    login = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"] == "valid-jwt"


def test_reusable_bearer_guard_profile_dashboard_and_logout(app_factory):
    auth = FakeAuth()
    client, _ = app_factory(auth=auth)
    assert client.get("/protected/profile").status_code == 401
    assert client.get("/protected/profile", headers={"Authorization": "Token invalid"}).status_code == 401
    assert client.get("/protected/profile", headers={"Authorization": "Bearer forged"}).status_code == 401

    headers = {"Authorization": "Bearer valid-jwt"}
    profile = client.get("/protected/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json() == {
        "id": "user-1",
        "email": "test@example.com",
        "created_at": "2026-09-29T00:00:00Z",
    }
    assert client.get("/protected/dashboard", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert auth.logged_out == ["valid-jwt"]


def test_refresh_and_openapi_bearer_scheme(app_factory):
    client, _ = app_factory()
    assert client.post("/auth/refresh", json={}).status_code == 400
    refreshed = client.post("/auth/refresh", json={"refresh_token": "refresh-jwt"})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] == "new-jwt"

    schema = client.get("/openapi.json").json()
    schemes = schema["components"]["securitySchemes"]
    assert any(item.get("scheme") == "bearer" for item in schemes.values())
    assert schema["paths"]["/protected/profile"]["get"]["security"]
