import logging
import uuid
import base64
import json
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_socketio import SocketIO, emit, join_room, leave_room
from typing import Dict, Any, List

from app.chat.session_manager import SessionInfo, session_manager
from app.services.aliyun_api import aliyun_service
from app.chat.scheduler import Scheduler
from app.chat.tasks import submit_task_to_worker
from app.file import temp_file_manager
from app.chat.redis_listener import init_redis_listener

# 创建调度器实例
scheduler = Scheduler()
socketio = SocketIO(cors_allowed_origins="*")
# 初始化日志
logger = logging.getLogger(__name__)

    
@socketio.on('connect')
def handle_connect():
    """处理客户端连接事件"""
    logger.info(f"客户端连接: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接事件"""
    logger.info(f"客户端断开连接: {request.sid}")
    
    # 查找与此连接相关的会话
    session_to_clean = None
    for session_id, session_info in list(session_manager.items()):
        if request.sid == session_id:
            session_to_clean = session_id
            break
    
    # 如果找到会话，执行清理
    if session_to_clean:
        handle_session_cleanup(session_to_clean)

@socketio.on('request_connection')
def handle_request_connection(data):
    """处理客户端请求连接事件"""
    try:
        logger.info(f"接收到连接请求: {data}")
        
        # 验证请求数据
        verify_jwt_in_request()
        # token = data.get('token')
        mode = data.get('mode')
        conversation_id = data.get('conversation_id')
        speech_rate = float(data.get('speech_rate', 1.0))
        pitch_rate = float(data.get('pitch_rate', 1.0))
        image_id = data.get('image_id')
        
        if not all([mode, conversation_id]):
            emit('error', {
                'code': 'INVALID_REQUEST',
                'message': '缺少必要参数'
            })
            return
            
        # 创建会话唯一标识（使用socket ID作为会话ID）
        session_id = request.sid
        
        # 创建会话信息
        session_info = SessionInfo(
            conversation_id=conversation_id,
            speech_rate=speech_rate,
            pitch_rate=pitch_rate,
            image_id=image_id,
            mode=mode
        )
        
        # 存储会话信息
        session_manager[session_id] = session_info
        
        # 将客户端加入以session_id命名的房间
        join_room(session_id)
        
        # 发送确认消息
        emit('connection_ack', {
            'session_id': session_id
        })
        
        logger.info(f"会话创建成功: {session_id}, 模式: {mode}")
        
    except Exception as e:
        logger.error(f"处理连接请求时出错: {str(e)}")
        emit('error', {
            'code': 'SERVER_ERROR',
            'message': f'服务器处理连接请求时出错: {str(e)}'
        })

@socketio.on('audio_stream_chunk')
def handle_audio_stream_chunk(data):
    """处理客户端发送的音频流片段"""
    try:
        session_id = request.sid
        
        # 检查会话是否存在
        if session_id not in session_manager:
            emit('error', {
                'code': 'SESSION_NOT_FOUND',
                'message': '会话不存在，请重新连接'
            })
            return
            
        # 获取会话信息
        session_info = session_manager[session_id]
        
        # 解码音频数据
        audio_chunk = base64.b64decode(data['chunk'])
        is_last = data.get('is_last', False)
        
        # 添加到会话的音频块缓存
        session_info.add_audio_chunk(audio_chunk)
        
        # 如果是最后一个块，则处理整个音频
        if is_last:
            success = session_info.save_audio_chunks()
            if success:
                # 处理完整音频（ASR、LLM、TTS等）
                process_complete_audio(session_id)
            else:
                emit('error', {
                    'code': 'AUDIO_PROCESSING_ERROR',
                    'message': '处理音频时出错'
                }, room=session_id)
        
    except Exception as e:
        logger.error(f"处理音频流片段时出错: {str(e)}")
        emit('error', {
            'code': 'SERVER_ERROR',
            'message': f'服务器处理音频时出错: {str(e)}'
        }, room=session_id)

@socketio.on('audio_uploaded')
def handle_audio_uploaded(data):
    """处理客户端上传音频完成事件"""
    try:
        audio_url = data.get('audio_url')
        session_id = data.get('session_id', request.sid)
        
        logger.info(f"接收到音频上传通知: {audio_url}, 会话ID: {session_id}")
        
        # 检查会话是否存在
        if session_id not in session_manager:
            emit('error', {
                'code': 'SESSION_NOT_FOUND',
                'message': '会话不存在，请重新连接'
            }, room=session_id)
            return
            
        # 处理完整音频（ASR、LLM、TTS等）
        process_complete_audio(session_id, audio_url)
        
    except Exception as e:
        logger.error(f"处理音频上传通知时出错: {str(e)}")
        emit('error', {
            'code': 'SERVER_ERROR',
            'message': f'服务器处理音频时出错: {str(e)}'
        }, room=session_id)

@socketio.on('stop_session')
def handle_stop_session(data):
    """处理客户端请求停止会话事件"""
    try:
        session_id = data.get('session_id', request.sid)
        
        logger.info(f"接收到停止会话请求: {session_id}")
        
        # 执行会话清理
        success = handle_session_cleanup(session_id)
        
        # 发送确认
        if success:
            emit('session_stopped_ack', {}, room=session_id)
        
    except Exception as e:
        logger.error(f"处理停止会话请求时出错: {str(e)}")
        emit('error', {
            'code': 'SERVER_ERROR',
            'message': f'服务器处理停止会话请求时出错: {str(e)}'
        }, room=session_id)

# 音频处理函数
def process_complete_audio(session_id, audio_url=None):
    """处理完整的音频文件"""
    try:
        # 获取会话信息
        session_info = session_manager[session_id]
        session_mode = session_info.mode
        
        # 如果没有提供音频URL，则使用会话中的最后一个音频消息
        if not audio_url:
            # 获取会话中最后添加的音频消息
            for message in reversed(session_info.messages):
                if message.get('role') == 'user' and message.get('content'):
                    for content_item in message.get('content', []):
                        if content_item.get('audio'):
                            audio_url = content_item.get('audio')
                            break
                    if audio_url:
                        break
        
        if not audio_url:
            raise Exception("找不到有效的音频URL")
            
        # 调用语音识别服务转为文本
        recognized_text = aliyun_service.recognize_audio(audio_url)
        
        # 记录转写结果并发送给客户端
        # 添加用户文本到会话历史
        session_info.messages.append({
            "role": "user",
            "content": [{"text": recognized_text}]
        })
        
        # 发送ASR结果给客户端
        emit('asr_result', {
            'user_text': recognized_text,
            'original_audio_url': audio_url
        }, room=session_id)
        
        # 根据不同的会话模式处理
        if session_mode == 'voice':
            # 语音聊天模式：流式TTS
            handle_voice_chat_mode(session_id, recognized_text)
        elif session_mode == 'video':
            # 视频聊天模式：调用视频生成
            handle_video_chat_mode(session_id, recognized_text)
        else:
            logger.error(f"未知的会话模式: {session_mode}")
            emit('error', {
                'code': 'INVALID_MODE',
                'message': f'未知的会话模式: {session_mode}'
            }, room=session_id)
        
    except Exception as e:
        logger.error(f"处理音频时出错: {str(e)}")
        emit('error', {
            'code': 'AUDIO_PROCESSING_ERROR',
            'message': f'处理音频时出错: {str(e)}'
        }, room=session_id)

def handle_voice_chat_mode(session_id, recognized_text):
    """处理语音聊天模式"""
    try:
        session_info = session_manager[session_id]
        
        # 定义TTS流回调函数
        def tts_stream_callback(audio_chunk, is_last):
            # 将二进制音频数据编码为Base64
            if audio_chunk:
                chunk_base64 = base64.b64encode(audio_chunk).decode('utf-8')
            else:
                chunk_base64 = ""
                
            # 发送音频块给客户端
            emit('tts_audio_stream', {
                'chunk': chunk_base64,
                'is_last': is_last,
                'format': 'mp3'  # 或根据实际格式调整
            }, room=session_id)
        
        # 流式调用TTS服务
        response_text = aliyun_service.audio_stream_mode(
            voice_id=session_info.voice_call_name,
            stream_callback=tts_stream_callback,
            speech_rate=session_info.speech_rate,
            pitch_rate=session_info.pitch_rate,
            messages=session_info.messages
        )
        # 记录AI回复到会话历史
        session_info.add_message("assistant", "text", response_text)
        
    except Exception as e:
        logger.error(f"处理语音聊天模式时出错: {str(e)}")
        emit('error', {
            'code': 'VOICE_CHAT_ERROR',
            'message': f'处理语音聊天时出错: {str(e)}'
        }, room=session_id)

def handle_video_chat_mode(session_id, recognized_text):
    """处理视频聊天模式"""
    try:
        session_info = session_manager[session_id]
        
        def tts_stream_callback(audio_chunk, is_last):
            if is_last:
                session_info.save_audio_chunks(is_response=True)

            else:
                session_info.add_audio_chunk(audio_chunk)
            
        # 流式调用TTS服务
        response_text = aliyun_service.audio_stream_mode(
            voice_id=session_info.voice_call_name,
            stream_callback=tts_stream_callback,
            speech_rate=session_info.speech_rate,
            pitch_rate=session_info.pitch_rate,
            messages=session_info.messages
        )
        # 记录AI回复到会话历史
        session_info.add_message("assistant", "text", response_text)
        
        # 准备任务数据
        task_payload = {
            'task_id': session_id,
            'session_id': session_id,
            'role_image_url': session_info.image_id,
            'audio_url': session_info.audio_id,
        }
        
        # 保存任务信息到会话
        session_info.task_info[session_id] = task_payload
        
        # 选择Worker队列
        target_queue = scheduler.select_worker_queue()
        if not target_queue:
            raise Exception("没有可用的Worker")
            
        # 提交任务到队列
        submit_success = submit_task_to_worker(queue_name=target_queue, task_data=task_payload)
        if not submit_success:
            raise Exception("提交任务失败")
            
        # 通知客户端任务已提交
        emit('task_submitted', {
            'task_id': session_id,
            'message': '视频生成任务已提交，请稍候...'
        }, room=session_id)
        
        logger.info(f"视频生成任务已提交: {session_id}")
        
    except Exception as e:
        logger.error(f"处理视频聊天模式时出错: {str(e)}")
        emit('error', {
            'code': 'VIDEO_CHAT_ERROR',
            'message': f'处理视频聊天时出错: {str(e)}'
        }, room=session_id)

def handle_session_cleanup(session_id):
    """清理会话资源"""
    try:
        # 检查会话是否存在
        if session_id not in session_manager:
            logger.warning(f"尝试清理不存在的会话: {session_id}")
            return False
            
        # 获取会话信息
        session_info = session_manager.pop(session_id, None)
        if not session_info:
            return False
        
        final_text = aliyun_service.conclude_chat(session_info.messages)
        if final_text:
            if session_info.insert_final_message(final_text):
                logger.info(f"插入最终消息成功: {final_text}")
            else:
                logger.error(f"插入最终消息失败: {final_text}")
            
        # 清理临时文件
        file_ids = session_info.temp_files
        if file_ids:
            success_count = temp_file_manager.delete_files(file_ids)
            logger.info(f"已清理 {success_count}/{len(file_ids)} 个会话临时文件")
        
        emit('session_stopped_ack', {
                "conclusion": final_text
            }, room=session_id) 
          
        # 让客户端离开房间
        leave_room(session_id)
        
        logger.info(f"会话已清理: {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"清理会话时出错: {str(e)}")
        return False
    
# 初始化Redis Pub/Sub监听
init_redis_listener(socketio)

logger.info("WebSocket路由初始化完成")
