# 认证模块初始化文件
from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

from . import routes