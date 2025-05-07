#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import json
import uuid
import threading
import time
from typing import Dict, Any, Optional
from functools import wraps
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import redis

# 导入服务
from app.services.chat_history_manager import ChatHistoryManager
from app.services.aliyun_api import AliyunAPIService
from app.services.file_service import FileService
from app.scheduler import Scheduler
from app.tasks import submit_task_to_worker

# 数据库模型
from app.models.conversation_model import Conversation
from app import db

logger = logging.getLogger(__name__)

# 初始化全局服务
socketio = SocketIO(cors_allowed_origins="*")
chat_manager = ChatHistoryManager()
aliyun_service = AliyunAPIService()
file_service = FileService()
scheduler = Scheduler()

# Redis监听线程
redis_listener_thread = None
redis_pubsub = None
redis_client = None
should_stop_listener = False

# Redis PubSub频道
REDIS_PUBSUB_CHANNEL = 'task_progress'

# 会话模式和角色信息存储
# 键: session_id, 值: {'mode': 'voice|video', 'role_id': 'xxx', 'conversation_id': 'xxx'}
session_info = {}

# 任务与用户会话的映射
# 键: task_id, 值: session_id
task_session_mapping = {}

# 辅助函数：记录关联的会话文件
# 键: session_id, 值: 文件路径列表
session_files = {}

def get_session_mode(session_id: str) -> Optional[str]:
    """获取会话模式"""
    if session_id in session_info:
        return session_info[session_id].get('mode')
    return None

def get_session_role_id(session_id: str) -> Optional[str]:
    """获取会话角色ID"""
    if session_id in session_info:
        return session_info[session_id].get('role_id')
    return None

def get_conversation_id(session_id: str) -> Optional[str]:
    """获取会话对应的conversation_id"""
    if session_id in session_info:
        return session_info[session_id].get('conversation_id')
    return None

def track_session_file(session_id: str, file_path: str) -> None:
    """记录会话关联的文件"""
    if session_id not in session_files:
        session_files[session_id] = []
    session_files[session_id].append(file_path)

def authenticated_only(f):
    """确保用户已认证的装饰器"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        # 这里可以添加JWT令牌验证，但简化起见，我们先不做复杂处理
        return f(*args, **kwargs)
    return wrapped

def init_redis_connection():
    """初始化Redis连接"""
    global redis_client, redis_pubsub
    
    try:
        # 从配置获取Redis连接信息
        redis_host = current_app.config.get('REDIS_HOST', 'localhost')
        redis_port = current_app.config.get('REDIS_PORT', 6379)
        redis_db = current_app.config.get('REDIS_DB', 0)
        
        # 创建Redis连接
        redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        
        # 创建PubSub对象
        redis_pubsub = redis_client.pubsub()
        
        # 订阅频道
        redis_pubsub.subscribe(REDIS_PUBSUB_CHANNEL)
        
        logger.info(f"Redis连接已初始化，订阅频道: {REDIS_PUBSUB_CHANNEL}")
        
    except Exception as e:
        logger.exception(f"初始化Redis连接时出错: {str(e)}")
        redis_client = None
        redis_pubsub = None

def handle_redis_message(message):
    """处理从Redis PubSub接收到的消息"""
    try:
        # 检查消息类型
        if message['type'] != 'message':
            return
        
        # 解析消息数据
        data = json.loads(message['data'].decode('utf-8'))
        
        # 获取任务ID和会话ID
        task_id = data.get('task_id')
        session_id = data.get('session_id')
        
        # 如果消息中没有session_id，尝试从映射中获取
        if not session_id and task_id in task_session_mapping:
            session_id = task_session_mapping[task_id]
        
        if not session_id:
            logger.warning(f"收到的消息没有有效的session_id: {data}")
            return
        
        # 根据消息的状态类型转发给客户端
        status = data.get('status')
        
        if status == 'processing' or status == 'progress':
            # 进度更新
            socketio.emit('task_progress', {
                'task_id': task_id,
                'status': status,
                'percentage': data.get('percentage', 0),
                'message': data.get('message', '处理中...')
            }, room=session_id)
            
        elif status == 'completed':
            # 完成通知
            video_url = data.get('video_url')
            
            if video_url:
                # 记录视频文件
                track_session_file(session_id, video_url)
                
                # 发送结果
                socketio.emit('task_result', {
                    'task_id': task_id,
                    'status': 'completed',
                    'video_url': video_url
                }, room=session_id)
                
                # 清理任务映射
                if task_id in task_session_mapping:
                    del task_session_mapping[task_id]
            else:
                socketio.emit('error', {
                    'task_id': task_id,
                    'message': '任务完成但没有返回视频URL'
                }, room=session_id)
                
        elif status == 'error':
            # 错误通知
            socketio.emit('error', {
                'task_id': task_id,
                'message': data.get('message', '处理任务时出错')
            }, room=session_id)
            
            # 清理任务映射
            if task_id in task_session_mapping:
                del task_session_mapping[task_id]
        
    except Exception as e:
        logger.exception(f"处理Redis消息时出错: {str(e)}")

def redis_listener_loop():
    """Redis PubSub监听循环"""
    global should_stop_listener, redis_pubsub
    
    logger.info("Redis监听线程已启动")
    
    while not should_stop_listener:
        try:
            if redis_pubsub:
                # 接收消息
                message = redis_pubsub.get_message(timeout=1)
                
                if message:
                    handle_redis_message(message)
            
            # 避免CPU占用过高
            time.sleep(0.01)
            
        except Exception as e:
            logger.exception(f"Redis监听循环中出错: {str(e)}")
            time.sleep(1)  # 出错后等待一秒再重试
    
    logger.info("Redis监听线程已结束")

def start_redis_listener():
    """启动Redis监听线程"""
    global redis_listener_thread, should_stop_listener
    
    if redis_listener_thread and redis_listener_thread.is_alive():
        logger.warning("Redis监听线程已经在运行")
        return
    
    # 初始化Redis连接
    init_redis_connection()
    
    # 重置停止标志
    should_stop_listener = False
    
    # 创建并启动监听线程
    redis_listener_thread = threading.Thread(target=redis_listener_loop)
    redis_listener_thread.daemon = True
    redis_listener_thread.start()
    
    logger.info("Redis监听器已启动")

def stop_redis_listener():
    """停止Redis监听线程"""
    global should_stop_listener, redis_pubsub
    
    # 设置停止标志
    should_stop_listener = True
    
    # 取消订阅
    if redis_pubsub:
        redis_pubsub.unsubscribe()
    
    logger.info("Redis监听器已停止")

@socketio.on('connect')
def on_connect():
    """处理客户端连接"""
    session_id = request.sid
    logger.info(f"客户端连接: {session_id}")

@socketio.on('disconnect')
def on_disconnect():
    """处理客户端断开连接"""
    session_id = request.sid
    logger.info(f"客户端断开连接: {session_id}")
    
    # 获取conversation_id
    conversation_id = get_conversation_id(session_id)
    if conversation_id:
        # 处理会话结束，生成总结并保存到数据库
        try:
            success = chat_manager.handle_session_end(session_id, conversation_id)
            logger.info(f"会话 {session_id} 结束处理: {'成功' if success else '失败'}")
        except Exception as e:
            logger.exception(f"处理会话结束时出错: {str(e)}")
    
    # 清理会话关联的临时文件
    try:
        files_to_clean = session_files.pop(session_id, [])
        for file_path in files_to_clean:
            try:
                filename = os.path.basename(file_path)
                file_service.delete_file(filename)
            except Exception as e:
                logger.exception(f"删除会话文件时出错: {str(e)}")
    except Exception as e:
        logger.exception(f"清理会话文件时出错: {str(e)}")
    
    # 清理会话信息
    if session_id in session_info:
        del session_info[session_id]

@socketio.on('request_connection')
@authenticated_only
def on_request_connection(data):
    """
    处理客户端请求连接
    
    期望的data格式:
    {
        "token": "user_auth_token_if_needed", 
        "mode": "voice | video", 
        "role_id": "fixed_role_identifier_for_session"
    }
    """
    try:
        session_id = request.sid
        
        # 提取请求数据
        mode = data.get('mode')
        role_id = data.get('role_id')
        user_id = data.get('user_id')  # 可能从JWT解析
        
        # 验证必要参数
        if not mode or not role_id:
            emit('error', {
                'message': '缺少必要参数: mode或role_id'
            })
            return
        
        # 创建或获取conversation
        try:
            conversation = Conversation(
                user_id=user_id,
                ai_role_id=role_id,
                interaction_mode=mode
            )
            db.session.add(conversation)
            db.session.commit()
            conversation_id = str(conversation.conversation_id)
        except Exception as e:
            logger.exception(f"创建会话记录时出错: {str(e)}")
            emit('error', {
                'message': f'创建会话记录失败: {str(e)}'
            })
            return
        
        # 存储会话信息
        session_info[session_id] = {
            'mode': mode,
            'role_id': role_id,
            'conversation_id': conversation_id,
            'user_id': user_id
        }
        
        # TODO: 获取AI角色详细信息
        # 这里应调用某个服务或直接查询数据库获取角色信息，包括名称、描述、图片URL等
        ai_role_info = {
            'role_id': role_id,
            'name': '默认角色名',
            'personality': '默认性格描述',
            'image_url': '/default_image.jpg'
        }
        
        # 发送连接确认
        emit('connection_ack', {
            'session_id': session_id,
            'mode': mode,
            'ai_role': ai_role_info,
            'chat_history': []  # 这里可以加载历史记录，但简化起见先返回空列表
        })
        
        logger.info(f"客户端 {session_id} 连接已确认: 模式={mode}, 角色ID={role_id}")
        
    except Exception as e:
        logger.exception(f"处理连接请求时出错: {str(e)}")
        emit('error', {
            'message': f'处理连接请求失败: {str(e)}'
        })

@socketio.on('audio_uploaded')
@authenticated_only
def on_audio_uploaded(data):
    """
    处理客户端上传音频的通知
    
    期望的data格式:
    {
        "audio_url": "publicly_accessible_url_to_the_uploaded_audio.wav", 
        "session_id": "user_session_identifier"
    }
    """
    try:
        # 提取请求数据
        audio_url = data.get('audio_url')
        session_id = data.get('session_id', request.sid)
        
        if not audio_url:
            emit('error', {
                'message': '缺少必要参数: audio_url'
            }, room=session_id)
            return
        
        # 检查会话模式和信息
        mode = get_session_mode(session_id)
        role_id = get_session_role_id(session_id)
        
        if not mode or not role_id:
            emit('error', {
                'message': '会话信息不完整，请重新连接'
            }, room=session_id)
            return
        
        # 记录用户音频到聊天历史
        chat_manager.add_user_audio(session_id, audio_url)
        
        # 调用语音识别
        try:
            recognized_text = aliyun_service.recognize_audio(audio_url)
            
            if not recognized_text:
                emit('error', {
                    'message': '语音识别失败，未能识别出文本'
                }, room=session_id)
                return
            
            # 记录识别文本到聊天历史
            chat_manager.add_user_text(session_id, recognized_text)
            
            # 发送ASR结果给客户端
            emit('asr_result', {
                'user_text': recognized_text,
                'original_audio_url': audio_url
            }, room=session_id)
            
        except Exception as e:
            logger.exception(f"语音识别时出错: {str(e)}")
            emit('error', {
                'message': f'语音识别失败: {str(e)}'
            }, room=session_id)
            return
        
        # 调用语音合成
        try:
            # 从角色信息中获取voice_id
            voice_id = None  # 实际应用中应从数据库获取
            
            synthesized_audio_url = aliyun_service.synthesize_speech(
                text=recognized_text, 
                voice_id=voice_id
            )
            
            if not synthesized_audio_url:
                emit('error', {
                    'message': '语音合成失败'
                }, room=session_id)
                return
            
            # 记录AI回复到聊天历史
            chat_manager.add_ai_response(session_id, recognized_text, synthesized_audio_url)
            
            # 记录生成的音频文件
            track_session_file(session_id, synthesized_audio_url)
            
        except Exception as e:
            logger.exception(f"语音合成时出错: {str(e)}")
            emit('error', {
                'message': f'语音合成失败: {str(e)}'
            }, room=session_id)
            return
        
        # 根据模式处理不同的流程
        if mode == 'voice':
            # 语音聊天模式：直接发送合成的音频
            emit('tts_audio', {
                'ai_text': recognized_text,
                'audio_url': synthesized_audio_url
            }, room=session_id)
            
        elif mode == 'video':
            # 视频聊天模式：提交视频生成任务
            try:
                # 生成任务ID
                task_id = str(uuid.uuid4())
                
                # 获取角色图片URL
                # 实际应用中应从数据库获取
                role_image_url = '/default_image.jpg'  # 临时使用默认值
                
                # 构建任务数据
                task_payload = {
                    'task_id': task_id,
                    'session_id': session_id,
                    'role_image_url': role_image_url,
                    'audio_url': synthesized_audio_url,
                    'text': recognized_text
                }
                
                # 记录任务与会话的映射关系
                task_session_mapping[task_id] = session_id
                
                # 调用调度器选择Worker队列
                target_queue = scheduler.select_worker_queue()
                if not target_queue:
                    emit('error', {
                        'message': '没有可用的Worker，请稍后再试'
                    }, room=session_id)
                    return
                
                # 提交任务到队列
                success = submit_task_to_worker(queue_name=target_queue, task_data=task_payload)
                if not success:
                    emit('error', {
                        'message': '提交任务失败，请稍后再试'
                    }, room=session_id)
                    # 清理任务映射
                    if task_id in task_session_mapping:
                        del task_session_mapping[task_id]
                    return
                
                # 通知客户端任务已提交
                emit('task_submitted', {
                    'task_id': task_id,
                    'message': '视频生成任务已提交...'
                }, room=session_id)
                
                logger.info(f"视频生成任务已提交: {task_id}")
                
            except Exception as e:
                logger.exception(f"提交视频生成任务时出错: {str(e)}")
                emit('error', {
                    'message': f'提交视频生成任务失败: {str(e)}'
                }, room=session_id)
                return
        
    except Exception as e:
        logger.exception(f"处理音频上传时出错: {str(e)}")
        emit('error', {
            'message': f'处理音频上传失败: {str(e)}'
        }, room=session_id)

@socketio.on('stop_session')
@authenticated_only
def on_stop_session(data):
    """
    处理客户端主动停止会话
    
    期望的data格式:
    {
        "session_id": "user_session_identifier"
    }
    """
    try:
        session_id = data.get('session_id', request.sid)
        
        # 获取conversation_id
        conversation_id = get_conversation_id(session_id)
        if not conversation_id:
            emit('error', {
                'message': '找不到会话记录'
            }, room=session_id)
            return
        
        # 处理会话结束，生成总结并保存到数据库
        success = chat_manager.handle_session_end(session_id, conversation_id)
        
        # 清理会话关联的临时文件
        files_to_clean = session_files.pop(session_id, [])
        for file_path in files_to_clean:
            try:
                filename = os.path.basename(file_path)
                file_service.delete_file(filename)
            except Exception as e:
                logger.exception(f"删除会话文件时出错: {str(e)}")
        
        # 清理会话信息
        if session_id in session_info:
            del session_info[session_id]
        
        # 发送确认
        emit('session_stopped_ack', {
            'message': '会话已结束'
        }, room=session_id)
        
        logger.info(f"会话 {session_id} 已主动结束: {'成功' if success else '失败'}")
        
    except Exception as e:
        logger.exception(f"处理停止会话时出错: {str(e)}")
        emit('error', {
            'message': f'处理停止会话失败: {str(e)}'
        }, room=session_id)

# 在应用初始化时启动Redis监听器
def initialize_socket_listeners(app):
    """初始化Socket和Redis监听器"""
    with app.app_context():
        start_redis_listener()
    
    # 注册应用关闭时的处理函数
    @app.teardown_appcontext
    def teardown_socket_listeners(exception=None):
        stop_redis_listener() 