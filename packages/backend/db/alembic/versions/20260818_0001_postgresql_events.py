"""PostgreSQL event tables

Revision ID: 20260818_0001
Revises:
Create Date: 2026-08-18
"""

import sqlalchemy as sa
from alembic import op

revision = "20260818_0001"
down_revision = None
branch_labels = None
depends_on = None


def event_identity_columns():
    return [
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("event_id", sa.UUID(), nullable=False, unique=True),
        sa.Column("course_id", sa.BigInteger(), nullable=False),
        sa.Column("assignment_id", sa.BigInteger(), nullable=False),
        sa.Column("student_key", sa.String(length=32), nullable=False),
        sa.Column("class_div", sa.String(length=64), nullable=False),
        sa.Column("hw_name", sa.String(length=255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "snapshot_event",
        *event_identity_columns(),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "file_size >= 0", name="ck_snapshot_event_file_size_nonnegative"
        ),
    )
    op.create_index(
        "ix_snapshot_assignment_student_file_time",
        "snapshot_event",
        [
            "assignment_id",
            "student_key",
            "relative_path",
            sa.text("occurred_at DESC"),
            sa.text("id DESC"),
        ],
    )
    op.create_index(
        "ix_snapshot_assignment_student_time",
        "snapshot_event",
        [
            "assignment_id",
            "student_key",
            sa.text("occurred_at DESC"),
            sa.text("id DESC"),
        ],
    )
    op.create_index(
        "ix_snapshot_assignment_time",
        "snapshot_event",
        ["assignment_id", sa.text("occurred_at DESC"), sa.text("id DESC")],
    )

    op.create_table(
        "build_event",
        *event_identity_columns(),
        sa.Column("cwd", sa.Text(), nullable=False),
        sa.Column("binary_path", sa.Text(), nullable=False),
        sa.Column("cmdline", sa.Text(), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_build_assignment_student_time",
        "build_event",
        [
            "assignment_id",
            "student_key",
            sa.text("occurred_at DESC"),
            sa.text("id DESC"),
        ],
    )
    op.create_index(
        "ix_build_assignment_time",
        "build_event",
        ["assignment_id", sa.text("occurred_at DESC"), sa.text("id DESC")],
    )

    op.create_table(
        "run_event",
        *event_identity_columns(),
        sa.Column("cmdline", sa.Text(), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=False),
        sa.Column("cwd", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("process_type", sa.String(length=32), nullable=False),
    )
    op.create_index(
        "ix_run_assignment_student_time",
        "run_event",
        [
            "assignment_id",
            "student_key",
            sa.text("occurred_at DESC"),
            sa.text("id DESC"),
        ],
    )
    op.create_index(
        "ix_run_assignment_time",
        "run_event",
        ["assignment_id", sa.text("occurred_at DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    op.drop_table("run_event")
    op.drop_table("build_event")
    op.drop_table("snapshot_event")
