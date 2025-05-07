#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import uuid
import datetime
from typing import Optional, Callable, Dict, Any

from dashscope.audio.tts_v2 import ResultCallback

logger = logging.getLogger(__name__)

class FileWriterCallback(ResultCallback):
    """
    将语音合成结果写入文件的回调处理类
    """
    
    def __init__(self, 
                 on_complete_callback: Optional[Callable[[str], None]] = None,
                 on_error_callback: Optional[Callable[[str], None]] = None):
        """
        初始化回调处理类
        
        Args:
            on_complete_callback: 当语音合成完成时的回调函数，参数为生成的音频文件URL
            on_error_callback: 当语音合成出错时的回调函数，参数为错误信息
        """
        self.on_complete_callback = on_complete_callback
        self.on_error_callback = on_error_callback
        
        # 生成唯一文件名
        unique_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.filename = f"tts_{timestamp}_{unique_id}.mp3"
        
        # 创建临时目录
        self.tmp_dir = os.environ.get('TMP_DIR', 'tmp/audio')
        os.makedirs(self.tmp_dir, exist_ok=True)
        
        self.output_path = os.path.join(self.tmp_dir, self.filename)
        self.file = None
        self.is_completed = False
        self.total_bytes = 0
    
    def get_file_url(self) -> str:
        """
        获取生成的音频文件URL
        
        Returns:
            str: 音频文件的URL
        """
        base_url = os.environ.get('BASE_URL', '')
        return f"{base_url}/tmp/audio/{self.filename}"
    
    def on_open(self):
        """WebSocket连接打开时调用"""
        logger.info(f"语音合成WebSocket连接已打开，将保存到: {self.output_path}")
        self.file = open(self.output_path, "wb")
    
    def on_complete(self):
        """语音合成任务完成时调用"""
        logger.info(f"语音合成任务完成，共接收 {self.total_bytes} 字节")
        self.is_completed = True
        if self.file:
            self.file.close()
        
        # 调用完成回调
        if self.on_complete_callback:
            try:
                self.on_complete_callback(self.get_file_url())
            except Exception as e:
                logger.error(f"执行on_complete_callback时发生错误: {str(e)}")
    
    def on_error(self, message: str):
        """语音合成任务出错时调用"""
        logger.error(f"语音合成任务失败: {message}")
        if self.file:
            self.file.close()
            
            # 如果文件存在但出错了，尝试删除它
            try:
                if os.path.exists(self.output_path):
                    os.remove(self.output_path)
            except Exception as e:
                logger.error(f"删除失败的语音文件时出错: {str(e)}")
        
        # 调用错误回调
        if self.on_error_callback:
            try:
                self.on_error_callback(message)
            except Exception as e:
                logger.error(f"执行on_error_callback时发生错误: {str(e)}")
    
    def on_close(self):
        """WebSocket连接关闭时调用"""
        logger.info(f"语音合成WebSocket连接已关闭")
        if self.file and not self.is_completed:
            self.file.close()
    
    def on_event(self, message):
        """收到事件消息时调用"""
        logger.debug(f"收到语音合成事件: {message}")
    
    def on_data(self, data: bytes) -> None:
        """收到音频数据时调用"""
        if self.file:
            try:
                self.file.write(data)
                self.total_bytes += len(data)
                logger.debug(f"接收到语音数据: {len(data)} 字节")
            except Exception as e:
                logger.error(f"写入语音数据时出错: {str(e)}") 