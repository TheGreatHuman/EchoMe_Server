from typing import Optional, Dict, Any
from datetime import datetime
import uuid                        # 标准库，用于 bytes ↔ UUID
from uuid6 import uuid7           # pip install uuid6
from app import db
from sqlalchemy import Column, VARCHAR, TIMESTAMP, BOOLEAN, TEXT, CheckConstraint, ForeignKey
from sqlalchemy.dialects.mysql import BINARY

class Voice(db.Model):
    __tablename__ = 'voices'

    # 在 Python 层生成有序 UUID v7，存为 16 字节二进制
    voice_id = Column(
        BINARY(16),
        primary_key=True,
        default=lambda: uuid7().bytes,
        nullable=False
    )
    @property
    def voice_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.voice_id))

    voice_name = Column(VARCHAR(50), nullable=False)

    # 外键引用 files.file_id，同样是 16 字节二进制
    voice_url = Column(
        BINARY(16),
        ForeignKey('files.file_id', ondelete='SET NULL'),
        nullable=False
    )
    @property
    def voice_url_str(self) -> str:
        return str(uuid.UUID(bytes=self.voice_url))

    created_at = Column(
        TIMESTAMP,
        nullable=False,
        default=datetime.utcnow
    )

    created_by = Column(
        BINARY(16),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    @property
    def created_by_user_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.created_by))

    is_public        = Column(BOOLEAN, nullable=False, default=False)
    call_name        = Column(VARCHAR(255), nullable=False)
    voice_gender     = Column(VARCHAR(6),  nullable=False)
    voice_description = Column(TEXT,       nullable=False)

    __table_args__ = (
        # 确保 gender 只能是 'male'/'female'/'other'
        CheckConstraint(
            voice_gender.in_(['male', 'female', 'other']),
            name='voice_gender_check'
        ),
    )

    # 关联到 User
    creator = db.relationship(
        'User',
        backref=db.backref('voices', lazy=True),
        foreign_keys=[created_by]
    )

    def __init__(
        self,
        voice_name: str,
        voice_url: Any,
        created_by: Any,
        call_name: str,
        voice_gender: str,
        voice_description: str,
        is_public: bool = False
    ):
        self.voice_name        = voice_name
        self.call_name         = call_name
        self.voice_gender      = voice_gender
        self.voice_description = voice_description
        self.is_public         = is_public

        # 将传入的 UUID 转成 bytes
        def to_bytes(val: Any) -> bytes:
            if isinstance(val, str):
                return uuid.UUID(val).bytes
            if isinstance(val, uuid.UUID):
                return val.bytes
            if isinstance(val, (bytes, bytearray)):
                return bytes(val)
            raise ValueError("Expected UUID str, uuid.UUID or bytes")

        self.voice_url   = to_bytes(voice_url)
        self.created_by  = to_bytes(created_by)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'voice_id':            self.voice_id_str,
            'voice_name':          self.voice_name,
            'voice_audition_url':  self.voice_url_str,
            'created_at':          self.created_at.isoformat() + 'Z',
            'created_by_user_id':  self.created_by_user_id_str,
            'is_public':           self.is_public,
            'call_name':           self.call_name,
            'voice_gender':        self.voice_gender,
            'voice_description':   self.voice_description
        }

