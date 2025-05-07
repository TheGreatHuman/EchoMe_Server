from flask import Blueprint

voice_bp = Blueprint('voice', __name__, url_prefix='/api/voice')

from . import routes