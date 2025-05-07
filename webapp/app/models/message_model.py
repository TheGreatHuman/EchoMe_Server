from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid                       # 标准库，用于 bytes ↔ UUID
from uuid6 import uuid7          # pip install uuid6
import json
from app import db
from sqlalchemy import Column, VARCHAR, TIMESTAMP, BOOLEAN, TEXT, CheckConstraint, ForeignKey, Integer
from sqlalchemy.dialects.mysql import BINARY

class Message(db.Model):
    __tablename__ = 'messages'

    # 在 Python 层生成有序 UUID v7，存为 16 字节二进制
    message_id = Column(
        BINARY(16),
        primary_key=True,
        default=lambda: uuid7().bytes,
        nullable=False
    )
    @property
    def message_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.message_id))

    conversation_id = Column(
        BINARY(16),
        ForeignKey('conversations.conversation_id', ondelete='CASCADE'),
        nullable=False
    )
    @property
    def conversation_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.conversation_id))

    type = Column(VARCHAR(6), nullable=False)
    content = Column(TEXT, nullable=False)
    is_user = Column(BOOLEAN, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    end_of_conversation = Column(TIMESTAMP, nullable=True)

    __table_args__ = (
        # 确保 type 只能是 'text', 'image', 'audio'
        CheckConstraint(
            type.in_(['text', 'image', 'audio']),
            name='message_type_check'
        ),
    )

    # 关联到 Conversation
    conversation = db.relationship(
        'Conversation',
        backref=db.backref('messages', lazy=True),
        foreign_keys=[conversation_id]
    )

    def __init__(
        self,
        conversation_id: Any,
        type: str,
        content: str,
        is_user: bool,
        end_of_conversation: Optional[datetime] = None
    ):
        self.type = type
        self.content = content
        self.is_user = is_user
        self.end_of_conversation = end_of_conversation

        # 将传入的 UUID 转成 bytes
        def to_bytes(val: Any) -> bytes:
            if isinstance(val, str):
                return uuid.UUID(val).bytes
            if isinstance(val, uuid.UUID):
                return val.bytes
            if isinstance(val, (bytes, bytearray)):
                return bytes(val)
            raise ValueError("Expected UUID str, uuid.UUID or bytes")

        self.conversation_id = to_bytes(conversation_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'message_id': self.message_id_str,
            'conversation_id': self.conversation_id_str,
            'type': self.type,
            'content': self.content,
            'is_user': self.is_user,
            'created_at': self.created_at.isoformat() + 'Z',
            'end_of_conversation': self.end_of_conversation.isoformat() + 'Z' if self.end_of_conversation else None
        }