"""add import_jobs table

Revision ID: 20260513_add_import_jobs
Revises: 20260513_add_uploads_table
Create Date: 2026-05-13 00:05:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260513_add_import_jobs'
down_revision = '20260513_add_uploads_table'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'import_jobs',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('logs', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_import_jobs_upload_id', 'import_jobs', ['upload_id'])
    op.create_index('ix_import_jobs_status', 'import_jobs', ['status'])
    op.create_foreign_key(
        'fk_import_jobs_upload_id_uploads', 'import_jobs', 'uploads', ['upload_id'], ['id'], ondelete='CASCADE'
    )


def downgrade():
    op.drop_constraint('fk_import_jobs_upload_id_uploads', 'import_jobs', type_='foreignkey')
    op.drop_index('ix_import_jobs_status', table_name='import_jobs')
    op.drop_index('ix_import_jobs_upload_id', table_name='import_jobs')
    op.drop_table('import_jobs'
)
