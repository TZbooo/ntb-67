"""delete telegram_users and move user_subdomains to users table

Revision ID: 206503703499
Revises: 77bec145e002
Create Date: 2026-07-28 05:04:26.988838

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from server.utils import generate_api_key


# revision identifiers, used by Alembic.
revision: str = '206503703499'
down_revision: Union[str, Sequence[str], None] = '77bec145e002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('telegram_users')
    op.drop_constraint(
        op.f('user_subdomains_user_id_fkey'),
        'user_subdomains',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'user_subdomains_user_id_fkey',
        'user_subdomains',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE',
    )

    op.add_column('users', sa.Column('api_key', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('max_tunnels', sa.Integer(), nullable=True))

    connection = op.get_bind()
    user_ids = connection.execute(sa.text('SELECT id FROM users')).fetchall()
    for (user_id,) in user_ids:
        connection.execute(
            sa.text('UPDATE users SET api_key = :api_key WHERE id = :id'),
            {'api_key': generate_api_key(), 'id': user_id},
        )

    connection.execute(sa.text('UPDATE users SET max_tunnels = 1 WHERE max_tunnels IS NULL'))

    op.alter_column('users', 'api_key', existing_type=sa.String(length=64), nullable=False)
    op.alter_column('users', 'max_tunnels', existing_type=sa.Integer(), nullable=False)
    op.create_unique_constraint('uq_users_api_key', 'users', ['api_key'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_users_api_key', 'users', type_='unique')
    op.drop_column('users', 'max_tunnels')
    op.drop_column('users', 'api_key')
    op.drop_constraint(
        'user_subdomains_user_id_fkey',
        'user_subdomains',
        type_='foreignkey',
    )
    op.create_foreign_key(
        op.f('user_subdomains_user_id_fkey'),
        'user_subdomains',
        'telegram_users',
        ['user_id'],
        ['tg_id'],
        ondelete='CASCADE',
    )
    op.create_table(
        'telegram_users',
        sa.Column('tg_id', sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('api_key', sa.VARCHAR(length=64), autoincrement=False, nullable=False),
        sa.Column(
            'max_tunnels',
            sa.INTEGER(),
            server_default=sa.text('1'),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('tg_id', name=op.f('telegram_users_pkey')),
        sa.UniqueConstraint(
            'api_key',
            name=op.f('telegram_users_api_key_key'),
            postgresql_include=[],
            postgresql_nulls_not_distinct=False,
        ),
    )
