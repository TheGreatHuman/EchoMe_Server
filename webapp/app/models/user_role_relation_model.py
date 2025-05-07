from typing import Optional
from datetime import datetime
import uuid
from uuid6 import uuid7
from app import db
from sqlalchemy import Column, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.mysql import BINARY

class UserRoleRelation(db.Model):
    __tablename__ = 'user_roles_relation'

    # 在 Python 层生成有序 UUID v7，存为 16 字节二进制
    id = Column(
        BINARY(16),
        primary_key=True,
        default=lambda: uuid7().bytes,
        nullable=False
    )
    @property
    def id_str(self) -> str:
        return str(uuid.UUID(bytes=self.id))

    user_id = Column(
        BINARY(16),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    @property
    def user_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.user_id))

    role_id = Column(
        BINARY(16),
        ForeignKey('ai_roles.role_id', ondelete='CASCADE'),
        nullable=False
    )
    @property
    def role_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.role_id))

    created_at = Column(
        TIMESTAMP,
        nullable=False,
        default=datetime.utcnow
    )

    # 关联到 User 和 AIRole
    user = db.relationship(
        'User',
        backref=db.backref('user_role_relations', lazy=True),
        foreign_keys=[user_id]
    )

    role = db.relationship(
        'AIRole',
        backref=db.backref('user_role_relations', lazy=True),
        foreign_keys=[role_id]
    )

    def __init__(self, user_id: str, role_id: str):
        """
        初始化用户角色关系
        
        Args:
            user_id: 用户ID（UUID字符串）
            role_id: 角色ID（UUID字符串）
        """
        self.user_id = uuid.UUID(user_id).bytes
        self.role_id = uuid.UUID(role_id).bytes

    def to_dict(self) -> dict:
        """
        将用户角色关系对象转换为字典
        """
        return {
            'id': self.id_str,
            'user_id': self.user_id_str,
            'role_id': self.role_id_str,
            'created_at': self.created_at.isoformat() + 'Z'
        }