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
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=10)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(hours=1)

    # 配置Redis
    app.config['REDIS_HOST'] = os.getenv('REDIS_HOST', 'localhost')
    app.config['REDIS_PORT'] = int(os.getenv('REDIS_PORT', 6379))
    app.config['REDIS_DB'] = int(os.getenv('REDIS_DB', 0))
    app.config['REDIS_PASSWORD'] = int(os.getenv('REDIS_PASSWORD', 0))
    app.config['PUBSUB_CHANNEL'] = os.getenv('PUBSUB_CHANNEL', 'task_progress')
    app.config['TASK_QUEUE_PREFIX'] = os.getenv('TASK_QUEUE_PREFIX', 'task_queue_gpu_')
    app.config['GPU_STATUS_PREFIX'] = os.getenv('GPU_STATUS_PREFIX', 'gpu_status:')
    app.config['MAX_WORKERS'] = int(os.getenv('MAX_WORKERS', 2))
    app.config['SCHEDULER_STRATEGY'] = os.getenv('SCHEDULER_STRATEGY', 'load_balance')
    
    # 配置文件服务
    app.config['TEMP_FILE_DIR'] = os.getenv('TEMP_FILE_DIR', 'temp')
    app.config['TEMP_FILE_EXPIRY'] = int(os.getenv('TEMP_FILE_EXPIRY', 24))

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
    
    # 初始化SocketIO
    from app.sockets import socketio, initialize_socket_listeners
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # 初始化Redis监听器
    with app.app_context():
        initialize_socket_listeners(app)
    
    return app