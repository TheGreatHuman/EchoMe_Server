#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import json
import tempfile
import time
from typing import List, Dict, Any, Optional, Callable, Union, Tuple, Generator, BinaryIO
import base64
import threading
import warnings
from queue import Queue
from http import HTTPStatus

import dashscope
from dashscope import Generation
from dashscope.audio.tts_v2 import SpeechSynthesizer, ResultCallback, AudioFormat
from dashscope import MultiModalConversation

logger = logging.getLogger(__name__)

class AliyunAPIService:
    """
    阿里云API服务封装，提供语音识别(ASR)和语音合成(TTS)能力
    """
    
    def __init__(self):
        """初始化阿里云API服务"""
        # 从环境变量获取API密钥
        api_key = os.getenv('DASHSCOPE_API_KEY')
        if not api_key:
            logger.warning("DASHSCOPE_API_KEY环境变量未设置，可能影响API调用")
        else:
            dashscope.api_key = api_key
            
        # 默认TTS模型和ASR模型
        self.tts_model = os.getenv('TTS_MODEL', 'cosyvoice-v1')
        self.asr_model = os.getenv('ASR_MODEL', 'qwen-audio-turbo-latest')
        self.llm_model = os.getenv('LLM_MODEL', 'qwen-plus')

    def text_chat_stream(
        self, 
        messages: List[Dict[str, Any]], 
        stream_callback: Callable[[str, bool], Generator]
    ) -> Generator[str, None, None]:
        """
        流式调用阿里云文本对话服务，通过回调函数实时返回生成的文本块
        
        Args:
            messages: 对话历史消息列表，格式为[{"role": "user|assistant|system", "content": "消息内容"}]
            stream_callback: 回调函数，接收(text_chunk, is_last)参数并返回Generator
            
        Returns:
            Generator: 生成器，生成流式结果
            
        Raises:
            Exception: 如果API调用失败
        """
        try:
            # 调用大模型API进行流式对话
            logger.info(f"调用文本对话API: {self.llm_model}")
            
            responses = Generation.call(
                model=self.llm_model,
                messages=messages,
                result_format="message",
                stream=True,
                incremental_output=True,
            )
            
            full_response = ""
            
            for response in responses:
                if response.status_code == HTTPStatus.OK:
                    # 获取当前文本块
                    text_chunk = response.output.choices[0].message.content
                    # 添加到完整响应中
                    full_response += text_chunk
                    # 回调处理函数
                    is_last = response.output.choices[0].finish_reason is not None
                    # 通过回调函数获取要发送的内容
                    for chunk in stream_callback(text_chunk, is_last):
                        yield chunk
                else:
                    logger.error(f"文本对话API调用失败: {response.message}")
                    for chunk in stream_callback(f"调用出错: {response.message}", True):
                        yield chunk
                    raise Exception(f"文本对话API调用失败: {response.message}")
            
            return full_response
            
        except Exception as e:
            logger.error(f"文本对话失败: {str(e)}")
            for chunk in stream_callback(f"服务异常: {str(e)}", True):
                yield chunk
            raise Exception(f"文本对话失败: {str(e)}")

    def conclude_chat(self, messages: List[Dict[str, Any]]) -> str:
        """
        总结本轮聊天的内容
        
        Args:
            messages: 对话历史
            
        Returns:
            str: 总结内容
            
        Raises:
            Exception: 如果API调用失败
        """
        try:
            need_conclude_messages = []
            for message in reversed(messages):
                if message['role'] == 'system':
                    need_conclude_messages.append(message)
                    break
                else:
                    need_conclude_messages.append(message)
            if len(need_conclude_messages) <= 2:
                return None
            need_conclude_messages.reverse()
            need_conclude_messages.append({
                "role": "user",
                "content": [{"text": "总结以上对话的内容"}]
            })

            
            # 调用ASR API
            response = MultiModalConversation.call(
                model=self.asr_model,
                messages=need_conclude_messages,
            )
            
            if response.status_code != 200:
                raise Exception(f"ASR API调用失败: {response.message}")
                
            # 提取识别文本
            recognized_text = response.output.choices[0]['message']['content'][0]['text']
            logger.info(f"ASR结果: {recognized_text}")
            return recognized_text
            
        except Exception as e:
            logger.error(f"语音识别失败: {str(e)}")
            raise Exception(f"语音识别失败: {str(e)}")

    
    class StreamCallback(ResultCallback):
        """TTS流式回调处理类"""
        
        def __init__(self, stream_callback):
            self.stream_callback = stream_callback
            self.is_open = False
            # 添加完成事件
            self.complete_event = threading.Event()
            
        def on_open(self):
            self.is_open = True
            logger.debug("TTS流式连接已建立")
            
        def on_data(self, data: bytes) -> None:
            # 回调上层处理函数处理音频块
            self.stream_callback(data, False)
            
        def on_complete(self):
            logger.debug("TTS流式合成完成")
            # 发送最后一个块标记
            self.stream_callback(b'', True)
            # 设置完成事件，通知等待的线程
            self.complete_event.set()
            
        def on_error(self, message: str):
            logger.error(f"TTS流式合成错误: {message}")
            # 发生错误时也设置事件，避免永久等待
            self.complete_event.set()
            
        def on_close(self):
            self.is_open = False
            logger.debug("TTS流式连接已关闭")
            
        def on_event(self, message):
            logger.debug(f"TTS流式事件: {message}")

    def audio_stream_mode(
            self, 
            voice_id: str, 
            stream_callback,
            speech_rate: float = 1.0, 
            pitch_rate: float = 1.0,
            messages: List[Dict[str, Any]] = None,
            format: AudioFormat = AudioFormat.MP3_22050HZ_MONO_256KBPS
        ) -> str:
        """
        流式调用阿里云语音合成服务，通过回调函数实时返回合成的音频块
        
        Args:
            voice_id: 音色ID
            stream_callback: 回调函数，接收(bytes, is_last)参数
            speech_rate: 语速，范围0.5~2.0
            pitch_rate: 音调，范围0.5~2.0
            format: 音频格式
            messages: 对话历史
        Returns:
            str: 回答文本
        Raises:
            Exception: 如果API调用失败
        """
        try:
            # 创建回调处理器
            callback = self.StreamCallback(stream_callback)
            
            # 创建合成器实例
            synthesizer = SpeechSynthesizer(
                model=self.tts_model,
                voice=voice_id,
                format=format,
                speech_rate=speech_rate,
                pitch_rate=pitch_rate,
                callback=callback
            )

            responses = MultiModalConversation.call(
                model="qwen-audio-turbo-latest", 
                messages=messages,
                stream=True,
                incremental_output=True,
                result_format="message"
            )
            response_text = ""

            logger.info("TTS流式合成开始")

            for response in responses:
                if response.status_code == HTTPStatus.OK:
                    if(response.output.choices[0]['finish_reason'] != 'stop'):

                        logger.info(f"TTS流式合成结果: {response}")
                        llm_text_chunk = response.output.choices[0]['message']['content'][0]['text']
                        response_text += llm_text_chunk
                        synthesizer.streaming_call(llm_text_chunk)
            synthesizer.streaming_complete()
            
            # 等待完成事件被设置，即等待on_complete被调用
            logger.info("等待TTS流式合成完成...")
            callback.complete_event.wait(timeout=60)  # 设置超时时间，避免永久阻塞
            logger.info("TTS流式合成已完成，函数返回")

            return response_text
            
            
        except Exception as e:
            logger.error(f"语音流式合成失败: {str(e)}")
            raise Exception(f"语音流式合成失败: {str(e)}")
        
    def audio_sync_mode(
            self, 
            voice_id: str, 
            speech_rate: float = 1.0, 
            pitch_rate: float = 1.0,
            messages: List[Dict[str, Any]] = None,
            format: AudioFormat = AudioFormat.MP3_22050HZ_MONO_256KBPS
        ) -> Tuple[bytes, str]:
        try:
        # 创建合成器实例
            synthesizer = SpeechSynthesizer(
                model=self.tts_model,
                voice=voice_id,
                format=format,
                speech_rate=1.0,
                pitch_rate=1.0,
            )

            response = MultiModalConversation.call(
                model="qwen-audio-turbo-latest", 
                messages=messages,
            )

            response_text = response.output.choices[0]['message']['content'][0]['text']
            logger.info(f"ALM结果: {response_text}")
            audio = synthesizer.call(response_text)

            return audio, response_text
        except Exception as e:
            logger.error(f"语音流式合成失败: {str(e)}")
            raise Exception(f"语音流式合成失败: {str(e)}")


# 创建全局实例
aliyun_service = AliyunAPIService()
