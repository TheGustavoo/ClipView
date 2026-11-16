import json
import subprocess
from pathlib import Path

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db import SessionLocal
from app.models import ProcessingJob, Project


@celery_app.task(name="app.tasks.processing.inspect_video", bind=True, max_retries=2)
def inspect_video(self, job_id: int) -> dict:
    db = SessionLocal()
    job = None
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return {"status": "missing", "job_id": job_id}

        project = db.get(Project, job.project_id)
        if project is None:
            job.status = "failed"
            job.error_message = "Projeto não encontrado."
            db.commit()
            return {"status": "failed", "job_id": job_id}

        source = Path(project.storage_path).resolve()
        upload_root = Path(settings.upload_dir).expanduser().resolve()
        if upload_root not in source.parents or not source.is_file():
            raise ValueError("Arquivo de origem inválido ou ausente.")

        job.status = "processing"
        job.error_message = None
        project.status = "processing"
        db.commit()

        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration,size,format_name:stream=codec_type,codec_name,width,height",
                "-of", "json", str(source),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=90,
        )
        metadata = json.loads(result.stdout)
        job.metadata_json = json.dumps(metadata, ensure_ascii=False)
        job.status = "completed"
        project.status = "ready"
        db.commit()
        return {"status": "completed", "job_id": job_id}
    except Exception as exc:
        db.rollback()
        if job is not None:
            job = db.get(ProcessingJob, job_id)
            project = db.get(Project, job.project_id) if job else None
            if job is not None:
                job.status = "failed"
                job.error_message = str(exc)[:500]
            if project is not None:
                project.status = "processing_failed"
            db.commit()
        raise
    finally:
        db.close()
