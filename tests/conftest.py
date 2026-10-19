"""Shared isolated database and HTTP client fixtures."""
import os
from pathlib import Path
import tempfile

os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-jwt-tests"
TEST_DB = Path(tempfile.gettempdir()) / "fitness_booking_api_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

import pytest
from fastapi.testclient import TestClient
from database import Base, engine
from database import SessionLocal
from main import app
from models import User
from sqlalchemy import select


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def signup_and_token(client, email="member@example.com", password="secure-password", role="member"):
    response = client.post("/signup", json={"name": "Test Member", "email": email, "password": password})
    assert response.status_code == 201
    if role != "member":
        db = SessionLocal()
        try:
            user = db.scalar(select(User).where(User.email == email))
            user.role = role
            db.commit()
        finally:
            db.close()
    login = client.post("/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
