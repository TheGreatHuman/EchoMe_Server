from flask import Blueprint

file_bp = Blueprint('file', __name__, url_prefix='/api/file')

from . import routes