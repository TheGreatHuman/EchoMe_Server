import os
import json
import logging
import threading
import time
import redis
from typing import Dict, Any

from app.chat.session_manager import session_manager
from app.file import temp_file_manager

logger = logging.getLogger(__name__)

class RedisListener:
    """监听Redis Pub/Sub通道，接收Worker发送的任务进度和结果"""
    
    def __init__(self, socketio=None):
        """初始化Redis监听器"""
        self.socketio = socketio
        self.running = False
        self.thread = None
        
        # Redis配置
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_db = int(os.getenv('REDIS_DB', 0))
        self.redis_password = os.getenv('REDIS_PASSWORD', None)
        
        # 通道名称
        self.pubsub_channel = os.getenv('PUBSUB_CHANNEL', 'task_progress')
        
        # 创建Redis连接
        self.redis_client = None
        self.pubsub = None
        
    def connect(self):
        """连接到Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True  # 自动解码为字符串
            )
            
            # 测试连接
            self.redis_client.ping()
            
            # 创建PubSub对象
            self.pubsub = self.redis_client.pubsub()
            
            logger.info(f"成功连接到Redis: {self.redis_host}:{self.redis_port}")
            return True
            
        except Exception as e:
            logger.error(f"连接Redis失败: {str(e)}")
            return False
            
    def start_listening(self):
        """开始监听Redis Pub/Sub通道"""
        if self.running:
            logger.warning("Redis监听器已经在运行")
            return False
            
        if not self.socketio:
            logger.error("未提供SocketIO实例，无法启动Redis监听器")
            return False
            
        if not self.connect():
            logger.error("无法连接到Redis，监听器未启动")
            return False
            
        # 订阅通道
        self.pubsub.subscribe(self.pubsub_channel)
        
        # 设置运行标志
        self.running = True
        
        # 创建并启动监听线程
        self.thread = threading.Thread(target=self._listen_loop)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"Redis监听器已启动，监听通道: {self.pubsub_channel}")
        return True
        
    def stop_listening(self):
        """停止监听"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.pubsub:
            self.pubsub.unsubscribe()
        if self.redis_client:
            self.redis_client.close()
        logger.info("Redis监听器已停止")
        
    def _listen_loop(self):
        """监听循环，处理接收到的消息"""
        try:
            while self.running:
                # 获取消息
                message = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                
                if message:
                    self._process_message(message)
                    
                time.sleep(0.01)  # 防止CPU占用过高
                
        except Exception as e:
            logger.error(f"Redis监听循环出错: {str(e)}")
            self.running = False
            
    def _process_message(self, message):
        """处理收到的消息"""
        try:
            # 解析消息数据
            if message['type'] != 'message':
                return
                
            data = json.loads(message['data'])
            
            # 提取关键信息
            status = data.get('status')
            task_id = data.get('task_id')
            session_id = data.get('session_id')
            
            if not all([status, task_id, session_id]):
                logger.warning(f"收到无效消息: {data}")
                return
                
            # 检查会话是否存在
            if session_id not in session_manager:
                logger.warning(f"消息对应的会话不存在: {session_id}")
                return
                
            # 根据事件类型处理
            if status == 'progress':
                # 处理任务进度消息
                self._handle_progress(data, session_id)
                
            elif status == 'completed':
                # 处理任务完成消息
                self._handle_completion(data, session_id)
                
            elif status == 'error':
                # 处理任务错误消息
                self._handle_error(data, session_id)
                
            else:
                logger.warning(f"未知的事件类型: {status}")
                
        except Exception as e:
            logger.error(f"处理Redis消息时出错: {str(e)}")
            
    def _handle_progress(self, data, session_id):
        """处理任务进度消息"""
        try:
            task_id = data.get('task_id')
            percentage = data.get('percentage', 0)
            status = data.get('status', 'processing')
            message = data.get('message', '处理中...')
            
            # 向客户端发送进度更新
            self.socketio.emit('task_progress', {
                'task_id': task_id,
                'status': status,
                'percentage': percentage,
                'message': message
            }, room=session_id)
            
            logger.debug(f"已发送任务进度更新: {task_id}, {percentage}%")
            
        except Exception as e:
            logger.error(f"处理任务进度消息出错: {str(e)}")
            
    def _handle_completion(self, data, session_id):
        """处理任务完成消息"""
        try:
            task_id = data.get('task_id')
            video_id = data.get('video_file_id')  # 可能是一个临时文件ID
            
            # 如果提供了视频ID，将其添加到会话的临时文件列表
            if video_id and session_id in session_manager:
                session_manager[session_id].temp_files.append(video_id)
            
            # 向客户端发送任务结果
            self.socketio.emit('video_result', {
                'task_id': task_id,
                'status': 'completed',
                'video_url': video_id
            }, room=session_id)
            
            logger.info(f"任务完成，ID: {task_id}")
            
        except Exception as e:
            logger.error(f"处理任务完成消息出错: {str(e)}")
            
    def _handle_error(self, data, session_id):
        """处理任务错误消息"""
        try:
            task_id = data.get('task_id')
            error_code = data.get('code', 'TASK_ERROR')
            error_message = data.get('message', '任务处理失败')
            
            # 向客户端发送错误消息
            self.socketio.emit('error', {
                'task_id': task_id,
                'code': error_code,
                'message': error_message
            }, room=session_id)
            
            logger.error(f"任务出错，ID: {task_id}, 错误: {error_message}")
            
        except Exception as e:
            logger.error(f"处理任务错误消息出错: {str(e)}")


# 创建全局实例（但不启动）
redis_listener = RedisListener()

def init_redis_listener(socketio):
    """初始化并启动Redis监听器"""
    redis_listener.socketio = socketio
    success = redis_listener.start_listening()
    return success 