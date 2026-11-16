from datetime import datetime
from pathlib import Path
import ipaddress
import socket
from urllib.parse import urlparse, unquote

import requests

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import ALLOWED_CONTENT_TYPES, has_video_signature, new_upload_path, upload_root
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


class ImportUrlRequest(BaseModel):
    url: str


def _validate_public_video_url(raw_url: str) -> tuple[str, str]:
    if len(raw_url) > 2048:
        raise HTTPException(status_code=422, detail="O link é muito longo.")
    parsed = urlparse(raw_url.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="Use um link HTTPS público e direto para o arquivo de vídeo.")
    if parsed.port not in (None, 443):
        raise HTTPException(status_code=422, detail="Porta não permitida no link.")
    host = parsed.hostname.rstrip(".").lower()
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise ValueError("host não público")
    except (OSError, ValueError):
        raise HTTPException(status_code=422, detail="O endereço do link não é público ou não pôde ser validado.")
    filename = unquote(Path(parsed.path).name) or "video.mp4"
    if Path(filename).suffix.lower() not in {".mp4", ".mov", ".webm", ".mkv"}:
        raise HTTPException(status_code=415, detail="O link precisa apontar diretamente para um arquivo MP4, MOV, WebM ou MKV.")
    return raw_url.strip(), filename


@router.post("/import-url", response_model=ProjectPublic, status_code=status.HTTP_201_CREATED)
def import_project_url(
    payload: ImportUrlRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectPublic:
    source_url, original_name = _validate_public_video_url(payload.url)
    try:
        response = requests.get(
            source_url,
            stream=True,
            allow_redirects=False,
            timeout=(10, 60),
            headers={"User-Agent": "ClipView/1.0 video-import"},
        )
        response.raise_for_status()
        if 300 <= response.status_code < 400:
            raise HTTPException(status_code=422, detail="O link redireciona para outro endereço. Use o link direto do arquivo.")
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail="O endereço não respondeu com um arquivo de vídeo compatível.")
        destination = new_upload_path(original_name)
        total = 0
        first_chunk = b""
        with destination.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                if not first_chunk:
                    first_chunk = chunk
                    if not has_video_signature(original_name, first_chunk):
                        raise HTTPException(status_code=415, detail="O conteúdo recebido não parece ser um vídeo válido.")
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="O vídeo excede o limite de 500 MB.")
                output.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="O endereço retornou um arquivo vazio.")
    except HTTPException:
        if "destination" in locals():
            destination.unlink(missing_ok=True)
        raise
    except requests.RequestException:
        if "destination" in locals():
            destination.unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail="Não foi possível baixar o vídeo desse endereço.")
    finally:
        if "response" in locals():
            response.close()

    try:
        project = Project(
            user_id=user.id,
            title=Path(original_name).stem[:160] or "Vídeo importado",
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
        except Exception:
            job.status = "dispatch_failed"
            job.error_message = "Fila de processamento indisponível. Verifique o Redis."
            project.status = "queue_unavailable"
            db.commit()
        return ProjectPublic(
            id=project.id, title=project.title, original_filename=project.original_filename,
            size_bytes=project.size_bytes, content_type=project.content_type,
            status=project.status, created_at=project.created_at, processing_job_id=job.id,
        )
    except Exception:
        destination.unlink(missing_ok=True)
        db.rollback()
        raise


@router.get("/{project_id}/video")
def stream_project_video(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    root = upload_root().resolve()
    video_path = Path(project.storage_path).resolve()
    if video_path.parent != root or not video_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado.")

    return FileResponse(
        path=video_path,
        media_type=project.content_type,
        filename=project.original_filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )


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
