"""temp_migration

Revision ID: 41cdafa531cf
Revises: 2da0dc469be8
Create Date: 2025-01-09 15:07:53.698762

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41cdafa531cf'
down_revision: Union[str, None] = '2da0dc469be8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        'refresh_tokens',
        'token',
        existing_type=sa.VARCHAR(length=64),
        type_=sa.String(length=512),
        existing_nullable=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        'refresh_tokens',
        'token',
        existing_type=sa.String(length=512),
        type_=sa.VARCHAR(length=64),
        existing_nullable=False,
    )
    # ### end Alembic commands ###
