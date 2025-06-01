#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from dotenv import load_dotenv
import eventlet
eventlet.monkey_patch()

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建应用
from app import create_app
from app.chat import socketio

app = create_app()

if __name__ == '__main__':
    # 获取端口
    port = int(os.getenv('PORT', 3000))
    
    # 使用SocketIO启动应用
    socketio.run(
        app,
        host='0.0.0.0', 
        port=port,
        debug=os.getenv('FLASK_ENV') == 'development',
        use_reloader=os.getenv('FLASK_ENV') == 'development',
        allow_unsafe_werkzeug=True
    )