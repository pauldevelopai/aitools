"""Add organization_profiles table and link users

Revision ID: 025
Revises: 024
Create Date: 2026-02-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # organization_profiles — platform user organizations
    op.create_table(
        'organization_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('jurisdiction', sa.String(), nullable=True),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('size', sa.String(), nullable=True),
        sa.Column('risk_tolerance', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "sector IN ('newsroom', 'ngo', 'academic', 'government', 'freelance', 'other')",
            name='ck_organization_profiles_sector',
        ),
        sa.CheckConstraint(
            "size IN ('small', 'medium', 'large', 'enterprise')",
            name='ck_organization_profiles_size',
        ),
        sa.CheckConstraint(
            "risk_tolerance IN ('low', 'medium', 'high')",
            name='ck_organization_profiles_risk_tolerance',
        ),
    )

    # Add organization_profile_id FK to users
    op.add_column(
        'users',
        sa.Column('organization_profile_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_users_organization_profile',
        'users',
        'organization_profiles',
        ['organization_profile_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_users_organization_profile_id',
        'users',
        ['organization_profile_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_users_organization_profile_id', table_name='users')
    op.drop_constraint('fk_users_organization_profile', 'users', type_='foreignkey')
    op.drop_column('users', 'organization_profile_id')
    op.drop_table('organization_profiles')
