"""Staff login with hashed passwords and revocable, database-backed sessions."""
import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Employee, StaffSession, utc_now

COOKIE_NAME = "produce_session"
SESSION_SECONDS = 8 * 60 * 60
PASSWORD_ITERATIONS = 600_000
# A small single-process login limiter for this local demo.
failed_logins = defaultdict(deque)
attempt_lock = threading.Lock()
ATTEMPT_WINDOW = 5 * 60
MAX_FAILURES = 10


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password, stored):
    try:
        algorithm, iterations, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


# Unknown codes still perform the expensive password check.
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def require_app_request(request: Request):
    # Cross-origin forms cannot send this header; cross-origin JS would require
    # a CORS preflight, which this API does not allow. Also protect login/logout.
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("X-Requested-With") != "ProduceDesk":
            raise HTTPException(403, "Request verification failed. Refresh the page and try again.")


def current_employee(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    session = db.get(StaffSession, token_hash(token)) if token else None
    if session is None or session.expires_at.replace(tzinfo=utc_now().tzinfo) <= utc_now():
        raise HTTPException(401, "Please sign in to continue.")
    employee = db.get(Employee, session.employee_id)
    if employee is None:
        raise HTTPException(401, "Please sign in to continue.")
    return employee


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_code: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("employee_code")
    @classmethod
    def normalize_code(cls, value):
        value = value.strip().upper()
        if not value:
            raise ValueError("Employee code is required.")
        return value


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_code: str
    full_name: str


router = APIRouter(prefix="/api/auth", tags=["Staff authentication"], dependencies=[Depends(require_app_request)])


@router.post("/login", response_model=EmployeeOut)
def login(payload: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "local"
    now = time.monotonic()
    with attempt_lock:
        # Prune inactive clients as well as expired attempts.
        for key in list(failed_logins):
            while failed_logins[key] and failed_logins[key][0] <= now - ATTEMPT_WINDOW:
                failed_logins[key].popleft()
            if not failed_logins[key]:
                del failed_logins[key]
        if len(failed_logins[client_ip]) >= MAX_FAILURES:
            raise HTTPException(429, "Too many sign-in attempts. Please try again in five minutes.")
        # Reserve a slot before password hashing so parallel attempts are limited.
        failed_logins[client_ip].append(now)
    employee = db.scalar(select(Employee).where(Employee.employee_code == payload.employee_code))
    valid = verify_password(payload.password, employee.password_hash if employee else DUMMY_HASH)
    if not valid or employee is None:
        raise HTTPException(401, "Employee code or password is incorrect.")
    with attempt_lock:
        if now in failed_logins[client_ip]:
            failed_logins[client_ip].remove(now)
    old_token = request.cookies.get(COOKIE_NAME)
    if old_token:
        db.execute(delete(StaffSession).where(StaffSession.token_hash == token_hash(old_token)))
    db.execute(delete(StaffSession).where(StaffSession.expires_at <= utc_now()))
    token = secrets.token_urlsafe(32)
    db.add(StaffSession(token_hash=token_hash(token), employee_id=employee.id,
                        expires_at=utc_now() + timedelta(seconds=SESSION_SECONDS)))
    db.commit()
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True,
                        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
                        samesite="strict", path="/api")
    response.headers["Cache-Control"] = "no-store"
    return employee


@router.get("/me", response_model=EmployeeOut)
def me(response: Response, employee: Employee = Depends(current_employee)):
    response.headers["Cache-Control"] = "no-store"
    return employee


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        db.execute(delete(StaffSession).where(StaffSession.token_hash == token_hash(token)))
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/api", httponly=True, samesite="strict")
    return {"message": "Signed out successfully."}
