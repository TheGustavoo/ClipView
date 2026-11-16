import json
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from faster_whisper import WhisperModel

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db import SessionLocal
from app.models import ProcessingJob, Project


@lru_cache(maxsize=2)
def get_whisper_model() -> WhisperModel:
    # The model is loaded once per worker process and reused by subsequent jobs.
    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


@celery_app.task(name="app.tasks.processing.inspect_video", bind=True, max_retries=2)
def inspect_video(self, job_id: int) -> dict:
    db = SessionLocal()
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

        probe = subprocess.run(
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
        metadata = json.loads(probe.stdout)
        duration = float(metadata.get("format", {}).get("duration") or 0)
        if duration > 7200:
            raise ValueError("Vídeos com mais de 2 horas ainda não são aceitos para transcrição.")

        audio_streams = [
            stream for stream in metadata.get("streams", [])
            if stream.get("codec_type") == "audio"
        ]
        job.metadata_json = json.dumps(metadata, ensure_ascii=False)

        if audio_streams:
            job.status = "extracting_audio"
            project.status = "transcribing"
            db.commit()

            with tempfile.NamedTemporaryFile(
                prefix=f"clipview-{job_id}-", suffix=".wav",
                dir=upload_root, delete=False,
            ) as temporary_audio:
                audio_path = Path(temporary_audio.name)

            try:
                subprocess.run(
                    [
                        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                        "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
                        "-c:a", "pcm_s16le", str(audio_path),
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=900,
                )

                job.status = "transcribing"
                db.commit()
                model = get_whisper_model()
                segments, info = model.transcribe(
                    str(audio_path),
                    beam_size=5,
                    vad_filter=True,
                )

                transcript_segments = []
                transcript_parts = []
                for segment in segments:
                    text = segment.text.strip()
                    if not text:
                        continue
                    transcript_parts.append(text)
                    transcript_segments.append({
                        "start": round(float(segment.start), 3),
                        "end": round(float(segment.end), 3),
                        "text": text,
                    })

                job.transcript_text = " ".join(transcript_parts)
                job.transcript_segments_json = json.dumps(
                    transcript_segments, ensure_ascii=False
                )
                job.language = info.language
            finally:
                audio_path.unlink(missing_ok=True)

        job.status = "completed"
        project.status = "ready"
        db.commit()
        return {"status": "completed", "job_id": job_id}
    except Exception as exc:
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job is not None:
            project = db.get(Project, job.project_id)
            job.status = "failed"
            job.error_message = str(exc)[:500]
            if project is not None:
                project.status = "processing_failed"
            db.commit()
        raise
    finally:
        db.close()
