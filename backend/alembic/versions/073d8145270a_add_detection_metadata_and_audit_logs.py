"""Add detection metadata and audit logs

Revision ID: 073d8145270a
Revises: 20260921_0003
Create Date: 2026-09-24 19:02:15.592129
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = '073d8145270a'
down_revision: Union[str, None] = '20260921_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Chỉ tạo bảng nếu nó chưa tồn tại
    if not inspector.has_table('audit_logs'):
        op.create_table('audit_logs',
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
        op.create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'], unique=False)
        op.create_index(op.f('ix_audit_logs_entity_type'), 'audit_logs', ['entity_type'], unique=False)
    
    # Quét xem các cột đã có sẵn chưa
    existing_cols = [c['name'] for c in inspector.get_columns('detections')]
    
    if 'image_content_type' not in existing_cols:
        op.add_column('detections', sa.Column('image_content_type', sa.String(length=50), nullable=False, server_default='image/jpeg'))
    if 'image_size_bytes' not in existing_cols:
        op.add_column('detections', sa.Column('image_size_bytes', sa.Integer(), nullable=True))
    if 'requires_confirmation' not in existing_cols:
        op.add_column('detections', sa.Column('requires_confirmation', sa.Boolean(), nullable=False, server_default='false'))
    if 'is_confirmed' not in existing_cols:
        op.add_column('detections', sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='false'))
    if 'confirmed_plate' not in existing_cols:
        op.add_column('detections', sa.Column('confirmed_plate', sa.String(length=50), nullable=True))
    if 'confirmed_by_id' not in existing_cols:
        op.add_column('detections', sa.Column('confirmed_by_id', sa.Uuid(), nullable=True))
    
    # Chỉ tạo Foreign Key trên Postgres
    if bind.engine.name != 'sqlite':
        op.create_foreign_key('fk_detections_confirmed_by_id_users', 'detections', 'users', ['confirmed_by_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    
    if bind.engine.name != 'sqlite':
        op.drop_constraint('fk_detections_confirmed_by_id_users', 'detections', type_='foreignkey')
        
    existing_cols = [c['name'] for c in inspector.get_columns('detections')]
    
    if 'confirmed_by_id' in existing_cols:
        op.drop_column('detections', 'confirmed_by_id')
    if 'confirmed_plate' in existing_cols:
        op.drop_column('detections', 'confirmed_plate')
    if 'is_confirmed' in existing_cols:
        op.drop_column('detections', 'is_confirmed')
    if 'requires_confirmation' in existing_cols:
        op.drop_column('detections', 'requires_confirmation')
    if 'image_size_bytes' in existing_cols:
        op.drop_column('detections', 'image_size_bytes')
    if 'image_content_type' in existing_cols:
        op.drop_column('detections', 'image_content_type')

    if inspector.has_table('audit_logs'):
        op.drop_index(op.f('ix_audit_logs_entity_type'), table_name='audit_logs')
        op.drop_index(op.f('ix_audit_logs_entity_id'), table_name='audit_logs')
        op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
        op.drop_table('audit_logs')