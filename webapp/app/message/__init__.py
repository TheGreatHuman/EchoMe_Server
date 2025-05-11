from flask import Blueprint

message_bp = Blueprint('message', __name__, url_prefix='/api/message')

from . import routes 