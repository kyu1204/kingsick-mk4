"""add_pnl_columns_to_backtest_trades

Revision ID: 201b679bd451
Revises: d1e2f3a4b5c6
Create Date: 2026-01-11 13:23:22.173117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '201b679bd451'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('backtest_trades', sa.Column('pnl', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('backtest_trades', sa.Column('pnl_pct', sa.Float(), nullable=True, server_default='0.0'))


def downgrade() -> None:
    op.drop_column('backtest_trades', 'pnl_pct')
    op.drop_column('backtest_trades', 'pnl')
