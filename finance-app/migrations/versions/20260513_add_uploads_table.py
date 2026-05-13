"""add uploads table and upload_id columns

Revision ID: 20260513_add_uploads_table
Revises: 
Create Date: 2026-05-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260513_add_uploads_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create uploads table
    op.create_table(
        'uploads',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('checksum', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rows_total', sa.Integer(), nullable=True),
        sa.Column('rows_inserted', sa.Integer(), nullable=True),
    )

    # Indexes for uploads
    op.create_index('ix_uploads_user_id', 'uploads', ['user_id'])
    op.create_index('ix_uploads_checksum', 'uploads', ['checksum'])

    # Add upload_id column to transactions
    op.add_column('transactions', sa.Column('upload_id', sa.Integer(), nullable=True))
    op.create_index('ix_transactions_upload_id', 'transactions', ['upload_id'])
    op.create_foreign_key(
        'fk_transactions_upload_id_uploads', 'transactions', 'uploads', ['upload_id'], ['id'], ondelete='SET NULL'
    )

    # Add upload_id column to categories
    op.add_column('categories', sa.Column('upload_id', sa.Integer(), nullable=True))
    op.create_index('ix_categories_upload_id', 'categories', ['upload_id'])
    op.create_foreign_key(
        'fk_categories_upload_id_uploads', 'categories', 'uploads', ['upload_id'], ['id'], ondelete='SET NULL'
    )


def downgrade():
    # Drop foreign keys and indexes, then columns
    op.drop_constraint('fk_categories_upload_id_uploads', 'categories', type_='foreignkey')
    op.drop_index('ix_categories_upload_id', table_name='categories')
    op.drop_column('categories', 'upload_id')

    op.drop_constraint('fk_transactions_upload_id_uploads', 'transactions', type_='foreignkey')
    op.drop_index('ix_transactions_upload_id', table_name='transactions')
    op.drop_column('transactions', 'upload_id')

    op.drop_index('ix_uploads_checksum', table_name='uploads')
    op.drop_index('ix_uploads_user_id', table_name='uploads')
    op.drop_table('uploads')
