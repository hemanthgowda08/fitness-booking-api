from datetime import datetime, timedelta, timezone
from jose import jwt
from database import SessionLocal
from models import User
from security import ALGORITHM, SECRET_KEY
from security import verify_password
from .conftest import signup_and_token


def test_signup_hashes_password_and_hides_it(client):
    response = client.post("/signup", json={"name": "Ada", "email": "ada@example.com", "password": "secure-password"})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "Ada", "email": "ada@example.com", "role": "member"}
    db = SessionLocal()
    try:
        user = db.get(User, 1)
        assert user.password_hash != "secure-password"
        assert verify_password("secure-password", user.password_hash)
    finally:
        db.close()


def test_duplicate_signup_is_rejected(client):
    signup_and_token(client)
    response = client.post("/signup", json={"name": "Again", "email": "member@example.com", "password": "secure-password"})
    assert response.status_code == 409


def test_public_signup_cannot_assign_a_privileged_role(client):
    response = client.post("/signup", json={"name": "Role Test", "email": "role@example.com", "password": "secure-password", "role": "admin"})
    assert response.status_code == 422
    response = client.post("/signup", json={"name": "Role Test", "email": "role@example.com", "password": "secure-password"})
    assert response.status_code == 201
    assert response.json()["role"] == "member"


def test_login_and_invalid_credentials(client):
    signup_and_token(client)
    assert client.post("/login", json={"email": "member@example.com", "password": "wrong-password"}).status_code == 401
    assert client.post("/login", json={"email": "nobody@example.com", "password": "secure-password"}).status_code == 401
    assert client.post("/login", json={"email": "member@example.com", "password": "secure-password"}).json()["token_type"] == "bearer"


def test_protected_routes_reject_missing_bad_and_expired_tokens(client):
    assert client.post("/classes", json={}).status_code == 401
    assert client.get("/bookings", headers={"Authorization": "Bearer malformed"}).status_code == 401
    expired = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, SECRET_KEY, algorithm=ALGORITHM)
    assert client.get("/bookings", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_me_returns_the_current_database_role(client):
    headers = signup_and_token(client, role="host")
    response = client.get("/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "host"
