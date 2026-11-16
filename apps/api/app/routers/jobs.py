import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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
    clip_suggestions: list[dict] | None
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
    suggestions = json.loads(job.clip_suggestions_json) if job.clip_suggestions_json else None
    return JobPublic(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        error_message=job.error_message,
        metadata=metadata,
        transcript=job.transcript_text,
        transcript_segments=segments,
        clip_suggestions=suggestions,
        language=job.language,
        created_at=job.created_at,
    )



class ClipTimingUpdate(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)


@router.patch("/{job_id}/clips/{clip_index}")
def update_clip_timing(
    job_id: int,
    clip_index: int,
    payload: ClipTimingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if payload.end <= payload.start:
        raise HTTPException(status_code=422, detail="O fim precisa ser posterior ao início.")

    job = db.scalar(
        select(ProcessingJob)
        .join(Project, ProcessingJob.project_id == Project.id)
        .where(ProcessingJob.id == job_id, Project.user_id == user.id)
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    suggestions = json.loads(job.clip_suggestions_json) if job.clip_suggestions_json else []
    if clip_index < 0 or clip_index >= len(suggestions):
        raise HTTPException(status_code=404, detail="Corte não encontrado.")

    duration = None
    if job.metadata_json:
        metadata = json.loads(job.metadata_json)
        duration = float(metadata.get("format", {}).get("duration") or 0)
    if duration and payload.end > duration:
        raise HTTPException(status_code=422, detail="O corte ultrapassa a duração do vídeo.")

    clip = suggestions[clip_index]
    clip["start"] = round(payload.start, 2)
    clip["end"] = round(payload.end, 2)
    clip["duration"] = round(payload.end - payload.start, 2)
    job.clip_suggestions_json = json.dumps(suggestions, ensure_ascii=False)
    db.commit()
    return {"clip_suggestions": suggestions}
