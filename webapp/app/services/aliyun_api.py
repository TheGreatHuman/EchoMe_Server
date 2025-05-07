#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import json
import tempfile
import uuid
from typing import Optional, Dict, Any, List
import requests
from flask import current_app
import dashscope
from dashscope import MultiModalConversation

logger = logging.getLogger(__name__)

class AliyunAPIService:
    """
    阿里云API服务，用于封装对Qwen-Audio和CosyVoice的调用
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化阿里云API服务
        
        Args:
            api_key: 阿里云DashScope API Key，如果不提供则从环境变量获取
        """
        # 从环境变量获取API Key或使用传入的API Key
        self.api_key = api_key or os.environ.get('DASHSCOPE_API_KEY')
        
        if not self.api_key:
            logger.warning("未提供DASHSCOPE_API_KEY，API调用将可能失败")
        else:
            dashscope.api_key = self.api_key
    
    def recognize_audio(self, audio_url: str) -> Optional[str]:
        """
        使用Qwen-Audio识别音频
        
        Args:
            audio_url: 音频URL
            
        Returns:
            Optional[str]: 识别的文本，如果失败则返回None
        """
        try:
            # 构建消息
            messages = [
                {'role': 'user', 'content': [{'audio': audio_url}]}
            ]
            
            # 调用API
            response = MultiModalConversation.call(
                model='qwen-audio-turbo-latest',
                messages=messages,
                result_format='message'
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"识别音频失败: Code={response.code}, Message={response.message}"
                logger.error(error_msg)
                return None
            
            # 提取文本
            text = ""
            if response.output and response.output.choices:
                for content_item in response.output.choices[0].message.content:
                    if "text" in content_item:
                        text += content_item["text"]
            
            return text
            
        except Exception as e:
            logger.exception(f"识别音频时出错: {str(e)}")
            return None
    
    def synthesize_speech(self, text: str, voice_id: Optional[str] = None) -> Optional[str]:
        """
        使用CosyVoice合成语音
        
        Args:
            text: 要合成的文本
            voice_id: 语音ID，如果不提供则使用默认语音
            
        Returns:
            Optional[str]: 合成的音频URL，如果失败则返回None
        """
        try:
            # 设置API端点和参数
            url = "https://dashscope.aliyuncs.com/api/v1/cosy/voice/tts"
            
            # 默认参数
            payload = {
                "model": "cosy-voice-v1",
                "input": {
                    "text": text
                },
                "parameters": {
                    "format": "wav",
                    "sample_rate": 24000
                }
            }
            
            # 如果提供了voice_id，添加到参数中
            if voice_id:
                payload["parameters"]["voice_id"] = voice_id
            
            # 设置请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 发送请求
            response = requests.post(url, json=payload, headers=headers)
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"合成语音失败: Status={response.status_code}, Response={response.text}"
                logger.error(error_msg)
                return None
            
            # 解析响应
            response_data = response.json()
            
            # 获取音频数据和保存
            audio_data = response_data.get("output", {}).get("audio", "")
            if not audio_data:
                logger.error("响应中没有音频数据")
                return None
            
            # 从FileService保存音频文件并获取URL
            from app.services.file_service import FileService
            file_service = FileService()
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            try:
                # 将Base64解码的音频数据写入文件
                import base64
                audio_binary = base64.b64decode(audio_data)
                temp_file.write(audio_binary)
                temp_file.close()
                
                # 生成唯一文件名
                unique_filename = f"{uuid.uuid4().hex}.wav"
                
                # 保存到目标目录
                file_path = os.path.join(file_service.temp_dir, unique_filename)
                import shutil
                shutil.copy2(temp_file.name, file_path)
                
                # 生成访问URL
                file_url = f"/api/chat/files/{unique_filename}"
                
                logger.info(f"语音合成文件已保存: {file_path}")
                return file_url
                
            finally:
                # 删除临时文件
                os.unlink(temp_file.name)
            
        except Exception as e:
            logger.exception(f"合成语音时出错: {str(e)}")
            return None 