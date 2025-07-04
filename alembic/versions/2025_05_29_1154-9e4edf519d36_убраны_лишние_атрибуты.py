"""убраны лишние атрибуты

Revision ID: 9e4edf519d36
Revises: 1bf56cdb0957
Create Date: 2025-05-29 11:54:10.063388

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9e4edf519d36'
down_revision: Union[str, None] = '1bf56cdb0957'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('accounts', 'openning_date')
    op.drop_column('clients', 'registration_date')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clients', sa.Column('registration_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=False))
    op.add_column('accounts', sa.Column('openning_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=False))
    # ### end Alembic commands ###
