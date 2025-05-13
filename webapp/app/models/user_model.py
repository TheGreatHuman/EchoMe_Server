from app import db
import bcrypt
from datetime import datetime
import uuid            # 标准库，用于 bytes → UUID 字符串
from uuid6 import uuid7
from sqlalchemy.dialects.mysql import BINARY

class User(db.Model):
    __tablename__ = 'users'
    
    # 用 uuid7() 在 Python 端生成有序的 16 字节 UUID
    id = db.Column(
        BINARY(16),
        primary_key=True,
        default=lambda: uuid7().bytes,
        nullable=False
    )
    # 只读属性：把 bytes 转成标准 UUID 格式字符串
    @property
    def id_str(self) -> str:
        return str(uuid.UUID(bytes=self.id))

    username     = db.Column(db.String(18),  nullable=False)
    phone_number = db.Column(db.String(11),  nullable=True)
    email        = db.Column(db.String(50),  nullable=True)
    password     = db.Column(db.String(255), nullable=False)
    theme_color  = db.Column(db.Integer,     nullable=True)

    avatar_url = db.Column(
        BINARY(16),
        # db.ForeignKey('files.file_id', ondelete='SET NULL'),
        nullable=True
    )
    @property
    def avatar_url_str(self) -> str | None:
        if self.avatar_url:
            return str(uuid.UUID(bytes=self.avatar_url))
        return None

    created_at    = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    last_login_at = db.Column(db.TIMESTAMP, nullable=True)
    
    def __init__(self, username: str, password: str,
                 phone_number: str | None = None,
                 email: str | None        = None):
        self.username     = username
        self.set_password(password)
        self.phone_number = phone_number
        self.email        = email
    
    def set_password(self, password: str) -> None:
        """设置加密密码"""
        self.password = bcrypt.hashpw(password.encode('utf-8'),
                                      bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'),
                              self.password.encode('utf-8'))
    
    def update_last_login(self) -> None:
        """更新最后登录时间（注意：建议由业务层统一 commit）"""
        self.last_login_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self) -> dict:
        """将用户对象转换为字典"""
        return {
            'id':            self.id_str,
            'username':      self.username,
            'phone_number':  self.phone_number,
            'email':         self.email,
            'theme_color':   self.theme_color,
            'avatar_url':    self.avatar_url_str,
            'created_at':    self.created_at.isoformat(),
            'last_login_at': (
                self.last_login_at.isoformat()
                if self.last_login_at else None
            )
        }
