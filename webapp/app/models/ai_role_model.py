from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid                       # 标准库，用于 bytes ↔ UUID
from uuid6 import uuid7          # pip install uuid6
import json
from app import db
from sqlalchemy import Column, VARCHAR, TIMESTAMP, BOOLEAN, TEXT, CheckConstraint, ForeignKey, Integer
from sqlalchemy.dialects.mysql import BINARY, JSON

class AIRole(db.Model):
    __tablename__ = 'ai_roles'

    # 在 Python 层生成有序 UUID v7，存为 16 字节二进制
    role_id = Column(
        BINARY(16),
        primary_key=True,
        default=lambda: uuid7().bytes,
        nullable=False
    )
    @property
    def role_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.role_id))

    name = Column(VARCHAR(50), nullable=False)
    gender = Column(VARCHAR(6), nullable=False)
    age = Column(Integer, nullable=True)
    personality = Column(TEXT, nullable=False)
    
    # 外键引用 files.file_id，同样是 16 字节二进制
    avatar_url = Column(
        BINARY(16),
        ForeignKey('files.file_id', ondelete='CASCADE'),
        nullable=False
    )
    @property
    def avatar_url_str(self) -> str:
        return str(uuid.UUID(bytes=self.avatar_url))

    voice_name = Column(VARCHAR(50), nullable=True)
    
    # 外键引用 voices.voice_id，同样是 16 字节二进制
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

    response_language = Column(VARCHAR(10), nullable=False)
    image_urls = Column(JSON, nullable=True)
    
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        default=datetime.utcnow
    )
    
    role_color = Column(Integer, nullable=True)
    
    # 注意: 此处列名可能是 'created_by' 的笔误，但保持与数据库一致
    created_by = Column(
        BINARY(16),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    @property
    def created_by_user_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.created_by))

    is_public = Column(BOOLEAN, nullable=False, default=False)
    used_num = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        # 确保 gender 只能是 'male'/'female'/'other'
        CheckConstraint(
            gender.in_(['male', 'female', 'other']),
            name='gender_check'
        ),
        # 确保 response_language 只能是 'chinese'/'english'
        CheckConstraint(
            response_language.in_(['chinese', 'english']),
            name='response_language_check'
        ),
    )

    # 关联到 User
    creator = db.relationship(
        'User',
        backref=db.backref('ai_roles', lazy=True),
        foreign_keys=[created_by]
    )

    def __init__(
        self,
        name: str,
        gender: str,
        personality: str,
        avatar_url: Any,
        response_language: str,
        created_by: Any,
        age: Optional[int] = None,
        voice_name: Optional[str] = None,
        voice_id: Optional[Any] = None,
        image_urls: Optional[List[str]] = None,
        role_color: Optional[int] = None,
        is_public: bool = False,
        used_num: int = 0
    ):
        self.name = name
        self.gender = gender
        self.personality = personality
        self.response_language = response_language
        self.age = age
        self.voice_name = voice_name
        self.role_color = role_color
        self.is_public = is_public
        self.used_num = used_num
        
        # 处理 image_urls (JSON 字段)
        if image_urls is None:
            self.image_urls = json.dumps([])
        else:
            self.image_urls = json.dumps(image_urls)

        # 将传入的 UUID 转成 bytes
        def to_bytes(val: Any) -> Optional[bytes]:
            if val is None:
                return None
            if isinstance(val, str):
                return uuid.UUID(val).bytes
            if isinstance(val, uuid.UUID):
                return val.bytes
            if isinstance(val, (bytes, bytearray)):
                return bytes(val)
            raise ValueError("Expected UUID str, uuid.UUID or bytes")

        self.avatar_url = to_bytes(avatar_url)
        self.voice_id = to_bytes(voice_id)
        self.created_by = to_bytes(created_by)

    def to_dict(self) -> Dict[str, Any]:
        # 处理 image_urls (从 JSON 字符串转为 Python 列表)
        image_urls_list = []
        if self.image_urls:
            try:
                if isinstance(self.image_urls, str):
                    image_urls_list = json.loads(self.image_urls)
                else:
                    # MySQL JSON 类型可能已经是 Python 对象
                    image_urls_list = self.image_urls
            except (json.JSONDecodeError, TypeError):
                image_urls_list = []

        return {
            'role_id': self.role_id_str,
            'name': self.name,
            'gender': self.gender,
            'age': self.age,
            'personality': self.personality,
            'avatar_url': self.avatar_url_str,
            'voice_name': self.voice_name,
            'voice_id': self.voice_id_str,
            'response_language': self.response_language,
            'image_urls': image_urls_list,
            'created_at': self.created_at.isoformat() + 'Z',
            'role_color': self.role_color,
            'created_by_user_id': self.created_by_user_id_str,
            'is_public': self.is_public,
            'used_num': self.used_num
        }