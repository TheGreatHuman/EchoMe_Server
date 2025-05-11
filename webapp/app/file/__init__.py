from flask import Blueprint

file_bp = Blueprint('file', __name__, url_prefix='/api/file')
temp_file_bp = Blueprint('tempfile', __name__, url_prefix='/api/tempfile')

from . import file_route
from . import temp_file_route
from .temp_file_route import get_file_path_type
from .temp_file_manager import temp_file_manager

# 注册临时文件蓝图
# file_bp.register_blueprint(temp_file_bp, url_prefix='/api/tempfile')