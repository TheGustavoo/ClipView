from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import ALLOWED_CONTENT_TYPES, has_video_signature, new_upload_path
from app.db import get_db
from app.dependencies import get_current_user
from app.models import Project, User

router = APIRouter(prefix="/projects", tags=["projects"])

class ProjectPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    original_filename: str
    size_bytes: int
    content_type: str
    status: str
    created_at: datetime

@router.get("", response_model=list[ProjectPublic])
def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Project]:
    return list(
        db.scalars(
            select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())
        ).all()
    )

@router.post("/upload", response_model=ProjectPublic, status_code=status.HTTP_201_CREATED)
async def upload_project(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    original_name = Path(file.filename or "video").name
    try:
        destination = new_upload_path(original_name)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))

    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Tipo de conteúdo não permitido.")

    total = 0
    try:
        first_chunk = await file.read(1024 * 1024)
        if not first_chunk:
            raise HTTPException(status_code=400, detail="O arquivo está vazio.")
        if not has_video_signature(original_name, first_chunk):
            raise HTTPException(status_code=415, detail="O arquivo não parece ser um vídeo MP4, MOV, WebM ou MKV.")

        with destination.open("wb") as output:
            total = len(first_chunk)
            if total > settings.max_upload_bytes:
                raise HTTPException(status_code=413, detail="O vídeo excede o limite de tamanho.")
            output.write(first_chunk)

            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="O vídeo excede o limite de tamanho.")
                output.write(chunk)

        project = Project(
            user_id=user.id,
            title=Path(original_name).stem[:160] or "Novo projeto",
            original_filename=original_name[:255],
            storage_path=str(destination),
            size_bytes=total,
            content_type=content_type,
            status="uploaded",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
