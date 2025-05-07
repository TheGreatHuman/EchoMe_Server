from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os
from datetime import timedelta

# 初始化SQLAlchemy
db = SQLAlchemy()

# 初始化JWTManager
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    
    # 配置CORS
    CORS(app)
    
    # 配置数据库
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "implicit_returning": True
    }
    
    # 配置JWT
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    # app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES')))
    # app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(seconds=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES')))
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=10)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(hours=1)


    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    
    # 注册蓝图
    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.voice import voice_bp # Import the new blueprint
    app.register_blueprint(voice_bp) # Register the new blueprint
    
    from app.file import file_bp
    app.register_blueprint(file_bp)
    
    from app.ai_role import ai_role_bp
    app.register_blueprint(ai_role_bp)

    from app.routes.chat_file_routes import chat_file_bp
    app.register_blueprint(chat_file_bp)

    from app.conversation import conversation_bp
    app.register_blueprint(conversation_bp)

    from app.message import message_bp
    app.register_blueprint(message_bp)
    
    return app