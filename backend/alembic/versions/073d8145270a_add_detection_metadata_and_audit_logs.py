"""Add detection metadata and audit logs

Revision ID: 073d8145270a
Revises: 20260921_0003
Create Date: 2026-09-24 19:02:15.592129
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '073d8145270a'
down_revision: Union[str, None] = '20260921_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    
    if 'audit_logs' not in insp.get_table_names():
        op.create_table('audit_logs',
            sa.Column('user_id', sa.Uuid(), nullable=True),
            sa.Column('action', sa.String(length=100), nullable=False),
            sa.Column('entity_type', sa.String(length=100), nullable=False),
            sa.Column('entity_id', sa.String(length=100), nullable=False),
            sa.Column('old_value', sa.JSON(), nullable=True),
            sa.Column('new_value', sa.JSON(), nullable=True),
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
        op.create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'], unique=False)
        op.create_index(op.f('ix_audit_logs_entity_type'), 'audit_logs', ['entity_type'], unique=False)
    
    # Kỹ thuật bọc thép: Chỉ thêm cột nếu nó chưa tồn tại để chống lỗi Duplicate Column trên CI
    if 'detections' in insp.get_table_names():
        columns = [c['name'] for c in insp.get_columns('detections')]
        if 'image_content_type' not in columns:
            op.add_column('detections', sa.Column('image_content_type', sa.String(length=50), nullable=False, server_default='image/jpeg'))
            op.add_column('detections', sa.Column('image_size_bytes', sa.Integer(), nullable=True))
            op.add_column('detections', sa.Column('requires_confirmation', sa.Boolean(), nullable=False, server_default='false'))
            op.add_column('detections', sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='false'))
            op.add_column('detections', sa.Column('confirmed_plate', sa.String(length=50), nullable=True))
            op.add_column('detections', sa.Column('confirmed_by_id', sa.Uuid(), nullable=True))
            
            if bind.engine.name != 'sqlite':
                op.create_foreign_key('fk_detections_confirmed_by_id_users', 'detections', 'users', ['confirmed_by_id'], ['id'], ondelete='SET NULL')

def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    
    # Bỏ qua việc xóa cột trên SQLite để chống lỗi "error in table after drop column"
    if bind.engine.name != 'sqlite':
        if 'detections' in insp.get_table_names():
            columns = [c['name'] for c in insp.get_columns('detections')]
            if 'image_content_type' in columns:
                op.drop_constraint('fk_detections_confirmed_by_id_users', 'detections', type_='foreignkey')
                op.drop_column('detections', 'confirmed_by_id')
                op.drop_column('detections', 'confirmed_plate')
                op.drop_column('detections', 'is_confirmed')
                op.drop_column('detections', 'requires_confirmation')
                op.drop_column('detections', 'image_size_bytes')
                op.drop_column('detections', 'image_content_type')
    
    if 'audit_logs' in insp.get_table_names():
        op.drop_index(op.f('ix_audit_logs_entity_type'), table_name='audit_logs')
        op.drop_index(op.f('ix_audit_logs_entity_id'), table_name='audit_logs')
        op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
        op.drop_table('audit_logs')