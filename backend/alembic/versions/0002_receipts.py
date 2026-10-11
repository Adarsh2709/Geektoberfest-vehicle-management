"""Add receipt attachment columns to maintenance records."""

import sqlalchemy as sa
from alembic import op

revision = "0002_receipts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("maintenance_records", sa.Column("receipt_path", sa.String(255), nullable=True))
    op.add_column("maintenance_records", sa.Column("receipt_content_type", sa.String(100), nullable=True))
    op.add_column("maintenance_records", sa.Column("receipt_size", sa.Integer(), nullable=True))
    op.add_column("maintenance_records", sa.Column("receipt_original_name", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("maintenance_records", "receipt_original_name")
    op.drop_column("maintenance_records", "receipt_size")
    op.drop_column("maintenance_records", "receipt_content_type")
    op.drop_column("maintenance_records", "receipt_path")
