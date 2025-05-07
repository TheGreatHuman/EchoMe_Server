from flask import Blueprint

conversation_bp = Blueprint('conversation', __name__, url_prefix='/api/conversation')

from app.conversation import routes 