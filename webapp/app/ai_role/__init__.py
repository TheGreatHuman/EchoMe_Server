from flask import Blueprint

ai_role_bp = Blueprint('ai_role', __name__, url_prefix='/api/ai_role')

from app.ai_role import routes