from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid                       # 标准库，用于 bytes ↔ UUID
from uuid6 import uuid7          # pip install uuid6
import json
from app import db
from sqlalchemy import Column, VARCHAR, TIMESTAMP, BOOLEAN, TEXT, CheckConstraint, ForeignKey, Integer
from sqlalchemy.dialects.mysql import BINARY, TINYINT

class Conversation(db.Model):
    __tablename__ = 'conversations'

    # 在 Python 层生成有序 UUID v7，存为 16 字节二进制
    conversation_id = Column(
        BINARY(16),
        primary_key=True,
        default=lambda: uuid7().bytes,
        nullable=False
    )
    @property
    def conversation_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.conversation_id))

    role_id = Column(
        BINARY(16),
        ForeignKey('ai_roles.role_id', ondelete='CASCADE'),
        nullable=False
    )
    @property
    def role_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.role_id))

    user_id = Column(
        BINARY(16),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    @property
    def user_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.user_id))

    title = Column(VARCHAR(50), nullable=True)
    last_message = Column(TEXT, nullable=True)
    last_message_time = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    voice_id = Column(
        BINARY(16),
        ForeignKey('voices.voice_id', ondelete='SET NULL'),
        nullable=True
    )
    @property
    def voice_id_str(self) -> Optional[str]:
        if self.voice_id:
            return str(uuid.UUID(bytes=self.voice_id))
        return None

    speech_rate = Column(TINYINT, nullable=False, default=10)
    pitch_rate = Column(TINYINT, nullable=False, default=10)

    __table_args__ = (
        # 确保 speech_rate 在 5-20 之间
        CheckConstraint(
            speech_rate.between(5, 20),
            name='speech_rate_check'
        ),
        # 确保 pitch_rate 在 5-20 之间
        CheckConstraint(
            pitch_rate.between(5, 20),
            name='pitch_rate_check'
        ),
    )

    # 关联到 AIRole, User 和 Voice
    role = db.relationship(
        'AIRole',
        backref=db.backref('conversations', lazy=True),
        foreign_keys=[role_id]
    )

    user = db.relationship(
        'User',
        backref=db.backref('conversations', lazy=True),
        foreign_keys=[user_id]
    )

    voice = db.relationship(
        'Voice',
        backref=db.backref('conversations', lazy=True),
        foreign_keys=[voice_id]
    )

    def __init__(
        self,
        role_id: Any,
        user_id: Any,
        title: Optional[str] = None,
        voice_id: Optional[Any] = None,
        speech_rate: int = 10,
        pitch_rate: int = 10
    ):
        self.title = title
        self.speech_rate = speech_rate
        self.pitch_rate = pitch_rate

        # 将传入的 UUID 转成 bytes
        def to_bytes(val: Any) -> bytes:
            if isinstance(val, str):
                return uuid.UUID(val).bytes
            if isinstance(val, uuid.UUID):
                return val.bytes
            if isinstance(val, (bytes, bytearray)):
                return bytes(val)
            raise ValueError("Expected UUID str, uuid.UUID or bytes")

        self.role_id = to_bytes(role_id)
        self.user_id = to_bytes(user_id)
        if voice_id:
            self.voice_id = to_bytes(voice_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'conversation_id': self.conversation_id_str,
            'role_id': self.role_id_str,
            'user_id': self.user_id_str,
            'title': self.title,
            'last_message': self.last_message,
            'last_message_time': self.last_message_time.isoformat() + 'Z' if self.last_message_time else None,
            'created_at': self.created_at.isoformat() + 'Z',
            'voice_id': self.voice_id_str,
            'speech_rate': self.speech_rate,
            'pitch_rate': self.pitch_rate
        }