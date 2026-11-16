"""Add speech transcription fields to processing jobs."""

from alembic import op
import sqlalchemy as sa

revision = "20261116_transcription"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "processing_jobs" not in inspector.get_table_names():
        # Fresh installations create the complete schema from current SQLAlchemy models.
        return

    existing = {column["name"] for column in inspector.get_columns("processing_jobs")}
    if "transcript_text" not in existing:
        op.add_column("processing_jobs", sa.Column("transcript_text", sa.Text(), nullable=True))
    if "transcript_segments_json" not in existing:
        op.add_column("processing_jobs", sa.Column("transcript_segments_json", sa.Text(), nullable=True))
    if "language" not in existing:
        op.add_column("processing_jobs", sa.Column("language", sa.String(length=16), nullable=True))
    if "clip_suggestions_json" not in existing:
        op.add_column("processing_jobs", sa.Column("clip_suggestions_json", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "processing_jobs" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("processing_jobs")}
    for column in ("clip_suggestions_json", "language", "transcript_segments_json", "transcript_text"):
        if column in existing:
            op.drop_column("processing_jobs", column)
