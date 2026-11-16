import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import ProcessingJob, Project, User

router = APIRouter(prefix="/jobs", tags=["processing"])


class JobPublic(BaseModel):
    id: int
    project_id: int
    status: str
    error_message: str | None
    metadata: dict | None
    transcript: str | None
    transcript_segments: list[dict] | None
    language: str | None
    created_at: datetime


@router.get("/{job_id}", response_model=JobPublic)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobPublic:
    job = db.scalar(
        select(ProcessingJob)
        .join(Project, ProcessingJob.project_id == Project.id)
        .where(ProcessingJob.id == job_id, Project.user_id == user.id)
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    metadata = json.loads(job.metadata_json) if job.metadata_json else None
    segments = json.loads(job.transcript_segments_json) if job.transcript_segments_json else None
    return JobPublic(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        error_message=job.error_message,
        metadata=metadata,
        transcript=job.transcript_text,
        transcript_segments=segments,
        language=job.language,
        created_at=job.created_at,
    )
