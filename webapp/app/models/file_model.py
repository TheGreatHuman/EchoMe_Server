from typing import Optional, Dict, Any
from datetime import datetime
import uuid                       # 标准库，用于 bytes ↔ UUID
from uuid6 import uuid7          # pip install uuid6
from app import db
from sqlalchemy import Column
from sqlalchemy.dialects.mysql import BINARY
from sqlalchemy import VARCHAR, TIMESTAMP, BOOLEAN, TEXT, ForeignKey

class File(db.Model):
    __tablename__ = 'files'

    # 在 Python 层生成有序 UUID（v7），存 BINARY(16)
    file_id = Column(
        BINARY(16),
        primary_key=True,
        default=lambda: uuid7().bytes,
        nullable=False
    )
    @property
    def file_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.file_id))

    file_name = Column(VARCHAR(255), nullable=False)
    file_path = Column(VARCHAR(255), nullable=False)
    file_size = Column(db.Integer, nullable=False)
    file_type = Column(VARCHAR(50), nullable=False)

    created_at = Column(
        TIMESTAMP,
        nullable=False,
        default=datetime.utcnow
    )

    # 外键仍指向 users.id（二进制 UUID）
    created_by = Column(
        BINARY(16),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    @property
    def created_by_user_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.created_by))

    is_public  = Column(BOOLEAN, nullable=False, default=True)
    description = Column(TEXT,    nullable=True)

    # 关联
    creator = db.relationship(
        'User',
        backref=db.backref('files', lazy=True),
        foreign_keys=[created_by]
    )

    def __init__(
        self,
        file_name: str,
        file_path: str,
        file_size: int,
        file_type: str,
        created_by: Any,
        is_public: bool = True,
        description: Optional[str] = None
    ):
        self.file_name   = file_name
        self.file_path   = file_path
        self.file_size   = file_size
        self.file_type   = file_type
        self.is_public   = is_public
        self.description = description

        # Python 层把 created_by 转成 bytes
        if isinstance(created_by, str):
            self.created_by = uuid.UUID(created_by).bytes
        elif isinstance(created_by, uuid.UUID):
            self.created_by = created_by.bytes
        elif isinstance(created_by, (bytes, bytearray)):
            self.created_by = bytes(created_by)
        else:
            raise ValueError(
                "created_by must be a UUID string, uuid.UUID or bytes"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_id':             self.file_id_str,
            'file_name':           self.file_name,
            'file_path':           self.file_path,
            'file_size':           self.file_size,
            'file_type':           self.file_type,
            'created_at':          self.created_at.isoformat(),
            'created_by_user_id':  self.created_by_user_id_str,
            'is_private':          self.is_public,
            'description':         self.description
        }
