from datetime import timedelta

import pytest
from sqlalchemy import select

from app.auth import COOKIE_NAME, MAX_FAILURES, hash_password, token_hash, verify_password
from app.models import Employee, StaffSession, utc_now
from app.seed import seed


def sign_in(client, **changes):
    return client.post("/api/auth/login", json={
        "employee_code": "TEST001", "password": "TestPassword123!", **changes})


@pytest.mark.parametrize("path", [
    "/api/config", "/api/orders", "/api/orders/1", "/api/orders/status-counts",
    "/api/customers", "/api/customers/1", "/api/customers/1/orders",
    "/api/products", "/api/deliveries?date_from=2026-10-15", "/api/auth/me",
])
def test_private_routes_require_login(anonymous_client, path):
    response = anonymous_client.get(path)
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Please sign in to continue."


def test_writes_require_login(anonymous_client):
    assert anonymous_client.post("/api/customers", json={
        "full_name": "Test", "phone": "123", "address": "Address"}).status_code == 401
    assert anonymous_client.patch("/api/orders/1", json={"status": "Packed"}).status_code == 401


def test_login_cookie_and_database_session(anonymous_client, employee, database):
    response = sign_in(anonymous_client, employee_code=" test001 ")
    assert response.status_code == 200
    assert response.json() == {"id": employee, "employee_code": "TEST001", "full_name": "Test Staff"}
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/api" in cookie
    assert cookie.startswith("__session=")
    assert "Max-Age=28800" in cookie
    token = anonymous_client.cookies.get(COOKIE_NAME)
    with database[1]() as db:
        assert db.get(StaffSession, token_hash(token)).employee_id == employee
        assert db.get(StaffSession, token) is None
        stored = db.get(Employee, employee).password_hash
        assert stored != "TestPassword123!" and verify_password("TestPassword123!", stored)
    assert anonymous_client.get("/api/auth/me").json()["employee_code"] == "TEST001"
    assert anonymous_client.get("/api/orders").status_code == 200


def test_bad_credentials_have_same_message(anonymous_client, employee):
    wrong_password = sign_in(anonymous_client, password="incorrect")
    wrong_code = sign_in(anonymous_client, employee_code="MISSING")
    assert wrong_password.status_code == wrong_code.status_code == 401
    assert wrong_password.json() == wrong_code.json()
    assert COOKIE_NAME not in anonymous_client.cookies


@pytest.mark.parametrize("changes", [{"employee_code": " "}, {"password": ""}, {"password": "x" * 257}])
def test_login_validation(anonymous_client, changes):
    assert sign_in(anonymous_client, **changes).status_code == 422


def test_logout_revokes_token(client, database):
    token = client.cookies.get(COOKIE_NAME)
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/api/orders").status_code == 401
    with database[1]() as db:
        assert db.get(StaffSession, token_hash(token)) is None


def test_expired_and_forged_sessions_are_rejected(client, database):
    token = client.cookies.get(COOKIE_NAME)
    with database[1]() as db:
        db.get(StaffSession, token_hash(token)).expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/orders").status_code == 401
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, "forged-token")
    assert client.get("/api/orders").status_code == 401


def test_login_rotates_existing_session(client, database):
    previous = client.cookies.get(COOKIE_NAME)
    assert sign_in(client).status_code == 200
    assert previous != client.cookies.get(COOKIE_NAME)
    with database[1]() as db:
        assert db.get(StaffSession, token_hash(previous)) is None


def test_csrf_header_required(client):
    assert client.post("/api/auth/logout", headers={"X-Requested-With": ""}).status_code == 403
    assert client.post("/api/auth/login", headers={"X-Requested-With": ""}, json={
        "employee_code": "TEST001", "password": "TestPassword123!"}).status_code == 403
    assert client.patch("/api/orders/1", headers={"X-Requested-With": ""}, json={"status": "Packed"}).status_code == 403


def test_failed_login_limit(anonymous_client, employee):
    for _ in range(MAX_FAILURES):
        assert sign_in(anonymous_client, password="wrong").status_code == 401
    assert sign_in(anonymous_client).status_code == 429


def test_seed_adds_login_to_existing_demo_without_reset(database):
    with database[1]() as db:
        db.connection().exec_driver_sql("PRAGMA user_version = 1")
        db.commit()
        seed(db)
        staff = db.scalar(select(Employee).where(Employee.employee_code == "NV001"))
        assert staff and verify_password("Produce@123", staff.password_hash)
        staff.password_hash = hash_password("ChangedPassword!")
        db.commit()
        seed(db)
        assert verify_password("ChangedPassword!", staff.password_hash)
        assert len(db.scalars(select(Employee)).all()) == 1


def test_password_salts_and_whitespace():
    first = hash_password(" password ")
    second = hash_password(" password ")
    assert first != second
    assert verify_password(" password ", first)
    assert not verify_password("password", first)


def test_api_responses_are_not_cached(client, anonymous_client):
    assert client.get("/api/orders").headers["cache-control"] == "private, no-store"
    client.post("/api/auth/logout")
    denied = client.get("/api/orders")
    assert denied.status_code == 401
    assert denied.headers["cache-control"] == "private, no-store"


def test_cloud_cookie_is_secure(anonymous_client, employee, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    response = sign_in(anonymous_client)
    assert "Secure" in response.headers["set-cookie"]
