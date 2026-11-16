from collections.abc import Generator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


def override_get_db() -> Generator:
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_register_login_and_me() -> None:
    email = f"{uuid4().hex}@example.com"
    registration = client.post(
        "/auth/register",
        json={"name": "Pessoa Teste", "email": email, "password": "uma-senha-segura-123"},
    )
    assert registration.status_code == 201
    token = registration.json()["access_token"]
    assert registration.json()["user"]["email"] == email

    profile = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == email

    login = client.post(
        "/auth/login",
        json={"email": email, "password": "uma-senha-segura-123"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_profile_requires_authentication() -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401
