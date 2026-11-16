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
from app.models import ProcessingJob, Project, User
from app.tasks.processing import inspect_video

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
    processing_job_id: int | None = None


@router.get("", response_model=list[ProjectPublic])
def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProjectPublic]:
    projects = db.scalars(
        select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())
    ).all()
    results = []
    for project in projects:
        job = db.scalar(
            select(ProcessingJob).where(ProcessingJob.project_id == project.id)
            .order_by(ProcessingJob.created_at.desc())
        )
        results.append(ProjectPublic(
            id=project.id,
            title=project.title,
            original_filename=project.original_filename,
            size_bytes=project.size_bytes,
            content_type=project.content_type,
            status=project.status,
            created_at=project.created_at,
            processing_job_id=job.id if job else None,
        ))
    return results


@router.post("/upload", response_model=ProjectPublic, status_code=status.HTTP_201_CREATED)
async def upload_project(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectPublic:
    original_name = Path(file.filename or "video").name
    try:
        destination = new_upload_path(original_name)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))

    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Tipo de conteúdo não permitido.")

    try:
        first_chunk = await file.read(1024 * 1024)
        if not first_chunk:
            raise HTTPException(status_code=400, detail="O arquivo está vazio.")
        if not has_video_signature(original_name, first_chunk):
            raise HTTPException(status_code=415, detail="O arquivo não parece ser um vídeo MP4, MOV, WebM ou MKV.")

        total = 0
        with destination.open("wb") as output:
            chunk = first_chunk
            while chunk:
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="O vídeo excede o limite de tamanho.")
                output.write(chunk)
                chunk = await file.read(1024 * 1024)

        project = Project(
            user_id=user.id,
            title=Path(original_name).stem[:160] or "Novo projeto",
            original_filename=original_name[:255],
            storage_path=str(destination),
            size_bytes=total,
            content_type=content_type,
            status="queued",
        )
        db.add(project)
        db.flush()

        job = ProcessingJob(project_id=project.id, status="queued")
        db.add(job)
        db.commit()
        db.refresh(project)
        db.refresh(job)

        try:
            inspect_video.delay(job.id)
        except Exception as exc:
            job.status = "dispatch_failed"
            job.error_message = "Não foi possível conectar à fila de processamento. Verifique o Redis e reinicie a tarefa."
            project.status = "queue_unavailable"
            db.commit()

        return ProjectPublic(
            id=project.id,
            title=project.title,
            original_filename=project.original_filename,
            size_bytes=project.size_bytes,
            content_type=project.content_type,
            status=project.status,
            created_at=project.created_at,
            processing_job_id=job.id,
        )
    except Exception:
        destination.unlink(missing_ok=True)
        db.rollback()
        raise
    finally:
        await file.close()
