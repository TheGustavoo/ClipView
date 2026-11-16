"""Add transcript-based clip suggestions to processing jobs."""

from alembic import op
import sqlalchemy as sa

revision = "20261116_clip_suggestions"
down_revision = "20261116_transcription"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "processing_jobs" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("processing_jobs")}
    if "clip_suggestions_json" not in existing:
        op.add_column(
            "processing_jobs",
            sa.Column("clip_suggestions_json", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "processing_jobs" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("processing_jobs")}
    if "clip_suggestions_json" in existing:
        op.drop_column("processing_jobs", "clip_suggestions_json")
