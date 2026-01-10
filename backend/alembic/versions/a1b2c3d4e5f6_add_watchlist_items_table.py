"""Add watchlist_items table

Revision ID: a1b2c3d4e5f6
Revises: 18bdc444226f
Create Date: 2026-01-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '18bdc444226f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('watchlist_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('stock_code', sa.String(length=6), nullable=False),
    sa.Column('stock_name', sa.String(length=100), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('target_price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('stop_loss_price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=True),
    sa.Column('memo', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'stock_code', name='uq_user_stock'),
    sa.CheckConstraint('target_price IS NULL OR target_price > 0', name='chk_target_price'),
    sa.CheckConstraint('stop_loss_price IS NULL OR stop_loss_price > 0', name='chk_stop_loss_price'),
    sa.CheckConstraint('quantity IS NULL OR quantity > 0', name='chk_quantity'),
    )
    op.create_index(op.f('ix_watchlist_items_user_id'), 'watchlist_items', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_watchlist_items_user_id'), table_name='watchlist_items')
    op.drop_table('watchlist_items')
