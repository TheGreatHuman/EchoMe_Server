#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from typing import Optional, Callable, List, Any

logger = logging.getLogger(__name__)

class WebSocketAudioPlayer:
    """
    通过WebSocket将音频数据实时传送给前端的播放器
    供AliyunAPIService.stream_llm_with_tts使用
    """
    
    def __init__(self, socket_emit_func: Callable[[str, Any, Optional[str]], None], 
                session_id: str, event_name: str = "audio_chunk"):
        """
        初始化WebSocket音频播放器
        
        Args:
            socket_emit_func: SocketIO emit函数，用于向客户端发送数据
                              函数签名应为 emit(event_name, data, room=session_id)
            session_id: 会话ID，用于标识接收音频数据的客户端
            event_name: 发送音频数据时使用的事件名称，默认为'audio_chunk'
        """
        self.socket_emit_func = socket_emit_func
        self.session_id = session_id
        self.event_name = event_name
        self.is_active = False
        self.total_chunks = 0
        self.total_bytes = 0
    
    def start(self):
        """开始音频流处理"""
        self.is_active = True
        self.total_chunks = 0
        self.total_bytes = 0
        logger.info(f"WebSocket音频播放器已启动，将向会话ID {self.session_id} 发送音频数据")
        
        # 发送一个开始事件给客户端，可用于初始化播放器
        self.socket_emit_func(
            f"{self.event_name}_start",
            {"status": "started"},
            self.session_id
        )
    
    def write(self, audio_data: bytes):
        """
        写入音频数据并通过WebSocket发送给客户端
        
        Args:
            audio_data: 音频数据字节
        """
        if not self.is_active:
            logger.warning("尝试写入音频数据到未启动的播放器")
            return
        
        # 音频数据需要使用Base64编码后才能通过WebSocket发送
        import base64
        encoded_data = base64.b64encode(audio_data).decode('utf-8')
        
        # 发送音频数据给客户端
        try:
            self.socket_emit_func(
                self.event_name,
                {
                    "audio_data": encoded_data,
                    "chunk_index": self.total_chunks,
                    "content_type": "audio/mpeg"
                },
                self.session_id
            )
            
            self.total_chunks += 1
            self.total_bytes += len(audio_data)
            logger.debug(f"发送音频数据块: {len(audio_data)} 字节 (总: {self.total_chunks} 块, {self.total_bytes} 字节)")
            
        except Exception as e:
            logger.error(f"发送音频数据时发生错误: {str(e)}")
    
    def stop(self):
        """停止音频流处理并发送结束信号"""
        if not self.is_active:
            return
        
        self.is_active = False
        
        # 发送结束事件给客户端
        try:
            self.socket_emit_func(
                f"{self.event_name}_end",
                {
                    "status": "completed",
                    "total_chunks": self.total_chunks,
                    "total_bytes": self.total_bytes
                },
                self.session_id
            )
            
            logger.info(f"WebSocket音频播放器已停止，共发送 {self.total_chunks} 个音频块，总计 {self.total_bytes} 字节")
            
        except Exception as e:
            logger.error(f"发送音频结束事件时发生错误: {str(e)}") 