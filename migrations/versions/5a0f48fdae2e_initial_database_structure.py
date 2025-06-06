"""Initial database structure

Revision ID: 5a0f48fdae2e
Revises: 
Create Date: 2025-05-12 13:28:47.304861

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a0f48fdae2e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('course_weight',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('course_code', sa.String(length=20), nullable=False),
    sa.Column('department', sa.String(length=100), nullable=False),
    sa.Column('weight', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('course_code')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('student_id', sa.String(length=20), nullable=False),
    sa.Column('department', sa.String(length=100), nullable=False),
    sa.Column('date_of_birth', sa.Date(), nullable=False),
    sa.Column('password', sa.String(length=60), nullable=False),
    sa.Column('is_verified', sa.Boolean(), nullable=True),
    sa.Column('user_type', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('otp_secret', sa.String(length=32), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('student_id')
    )
    op.create_table('course_directory',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('department', sa.String(length=100), nullable=False),
    sa.Column('course_code', sa.String(length=20), nullable=False),
    sa.Column('actual_weight', sa.Float(), nullable=False),
    sa.Column('current_weight', sa.Float(), nullable=False),
    sa.Column('course_day', sa.String(length=20), nullable=False),
    sa.Column('course_time_start', sa.Time(), nullable=False),
    sa.Column('course_time_end', sa.Time(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['course_code'], ['course_weight.course_code'], ),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sender_id', sa.Integer(), nullable=False),
    sa.Column('receiver_id', sa.Integer(), nullable=False),
    sa.Column('subject', sa.String(length=200), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('is_closed', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['messages.id'], ),
    sa.ForeignKeyConstraint(['receiver_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('identifier', sa.String(length=50), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('identifier')
    )
    op.drop_table('user')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('username', sa.VARCHAR(length=20), nullable=False),
    sa.Column('email', sa.VARCHAR(length=120), nullable=False),
    sa.Column('password', sa.VARCHAR(length=60), nullable=False),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.drop_table('notifications')
    op.drop_table('messages')
    op.drop_table('course_directory')
    op.drop_table('users')
    op.drop_table('course_weight')
    # ### end Alembic commands ###
