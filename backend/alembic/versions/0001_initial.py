"""Create users, vehicles, and maintenance records."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("username"), sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("make", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False), sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("registration_number", sa.String(30), nullable=False), sa.Column("current_mileage", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("registration_number"),
    )
    op.create_index("ix_vehicles_registration_number", "vehicles", ["registration_number"])
    op.create_index("ix_vehicles_owner_id", "vehicles", ["owner_id"])
    op.create_table(
        "maintenance_records",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False), sa.Column("mileage", sa.Integer(), nullable=False),
        sa.Column("service_type", sa.String(100), nullable=False), sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cost", sa.Numeric(10, 2), nullable=False), sa.Column("next_service_date", sa.Date(), nullable=True),
        sa.Column("next_service_mileage", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_maintenance_records_vehicle_id", "maintenance_records", ["vehicle_id"])


def downgrade():
    op.drop_index("ix_maintenance_records_vehicle_id", table_name="maintenance_records")
    op.drop_table("maintenance_records")
    op.drop_index("ix_vehicles_owner_id", table_name="vehicles")
    op.drop_index("ix_vehicles_registration_number", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
