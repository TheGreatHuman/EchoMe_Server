import random
import string
from datetime import datetime, timedelta
import os
from email_validator import validate_email, EmailNotValidError
import re

class CaptchaManager:
    """验证码管理类"""
    _captcha_store = {}  # 存储验证码的字典 {identifier: {code: str, expire_time: datetime, type: str}}
    
    @classmethod
    def generate_captcha(cls, identifier, type_):
        """生成验证码
        
        Args:
            identifier: 手机号或邮箱
            type_: 'phone' 或 'email'
            
        Returns:
            str: 生成的验证码
        """
        # 生成6位数字验证码
        code = ''.join(random.choices(string.digits, k=6))
        
        # 设置过期时间
        expire_seconds = int(os.getenv('CAPTCHA_EXPIRE', 300))
        expire_time = datetime.now() + timedelta(seconds=expire_seconds)
        
        # 存储验证码
        cls._captcha_store[identifier] = {
            'code': code,
            'expire_time': expire_time,
            'type': type_
        }
        
        return code
    
    @classmethod
    def verify_captcha(cls, identifier, code):
        """验证验证码
        
        Args:
            identifier: 手机号或邮箱
            code: 用户输入的验证码
            
        Returns:
            bool: 验证是否成功
        """
        if identifier not in cls._captcha_store:
            return False
        
        captcha_info = cls._captcha_store[identifier]
        
        # 检查是否过期
        if datetime.now() > captcha_info['expire_time']:
            # 删除过期验证码
            del cls._captcha_store[identifier]
            return False
        
        # 验证码匹配检查
        if captcha_info['code'] == code:
            # 验证成功后删除验证码
            del cls._captcha_store[identifier]
            return True
        
        return False

    @classmethod
    def is_first_use(cls, identifier, type_):
        """检查是否是首次使用（需要注册）
        
        在实际应用中，这里应该查询数据库判断用户是否存在
        """
        from app.models.user_model import User
        from app import db
        
        if type_ == 'phone':
            user = User.query.filter_by(phone_number=identifier).first()
        else:  # email
            user = User.query.filter_by(email=identifier).first()
        
        return user is None

def validate_phone(phone):
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'  # 中国大陆手机号格式
    return bool(re.match(pattern, phone))

def validate_identifier(identifier, type_):
    """验证标识符（手机号或邮箱）格式
    
    Args:
        identifier: 手机号或邮箱
        type_: 'phone' 或 'email'
        
    Returns:
        tuple: (是否有效, 错误信息)
    """
    if type_ == 'phone':
        if validate_phone(identifier):
            return True, None
        return False, "Invalid phone number format"
    
    elif type_ == 'email':
        try:
            validate_email(identifier)
            return True, None
        except EmailNotValidError as e:
            return False, str(e)
    
    return False, "Invalid identifier type, must be 'phone' or 'email'"