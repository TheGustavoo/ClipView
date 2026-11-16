from collections.abc import Generator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db import Base, get_db
from app.main import app
from app.models import ProcessingJob

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

def create_user_token() -> str:
    email = f"{uuid4().hex}@example.com"
    response = client.post(
        "/auth/register",
        json={"name": "Teste Upload", "email": email, "password": "senha-de-teste-123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]

def test_upload_and_list_projects(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr("app.routers.projects.inspect_video.delay", lambda job_id: None)
    token = create_user_token()
    headers = {"Authorization": f"Bearer {token}"}
    mp4_header = b"\x00\x00\x00\x18ftypisom" + b"sample-video-data"
    upload = client.post(
        "/projects/upload",
        headers=headers,
        files={"file": ("amostra.mp4", mp4_header, "video/mp4")},
    )
    assert upload.status_code == 201
    project = upload.json()
    assert project["original_filename"] == "amostra.mp4"
    assert project["status"] == "queued"
    assert project["processing_job_id"] is not None

    video = client.get(f"/projects/{project['id']}/video", headers=headers)
    assert video.status_code == 200
    assert video.content == mp4_header
    ranged_video = client.get(
        f"/projects/{project['id']}/video",
        headers={**headers, "Range": "bytes=0-5"},
    )
    assert ranged_video.status_code == 206
    assert ranged_video.content == mp4_header[:6]
    assert ranged_video.headers["content-range"] == f"bytes 0-5/{len(mp4_header)}"
    job = client.get(f"/jobs/{project['processing_job_id']}", headers=headers)
    assert job.status_code == 200
    assert job.json()["status"] == "queued"

    db = TestingSessionLocal()
    processing_job = db.get(ProcessingJob, project["processing_job_id"])
    processing_job.clip_suggestions_json = '[{"start": 1.0, "end": 8.0, "duration": 7.0, "score": 0.8, "text": "Trecho de teste", "reasons": ["Pergunta"]}]'
    db.commit()
    db.close()
    edited = client.patch(
        f"/jobs/{project['processing_job_id']}/clips/0",
        headers=headers,
        json={"start": 2.5, "end": 9.0},
    )
    assert edited.status_code == 200
    assert edited.json()["clip_suggestions"][0]["start"] == 2.5
    assert edited.json()["clip_suggestions"][0]["end"] == 9.0

    listing = client.get("/projects", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

def test_upload_requires_authentication() -> None:
    response = client.post(
        "/projects/upload",
        files={"file": ("amostra.mp4", b"video", "video/mp4")},
    )
    assert response.status_code == 401

def test_upload_rejects_unsupported_extension() -> None:
    token = create_user_token()
    response = client.post(
        "/projects/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("script.exe", b"not-video", "application/octet-stream")},
    )
    assert response.status_code == 415

def test_upload_rejects_invalid_container_signature() -> None:
    token = create_user_token()
    response = client.post(
        "/projects/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("renamed.mp4", b"this is not a video", "video/mp4")},
    )
    assert response.status_code == 415


def test_video_playback_requires_authentication() -> None:
    response = client.get("/projects/1/video")
    assert response.status_code == 401
