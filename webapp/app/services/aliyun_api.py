#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from typing import Optional, Dict, Any, Union, Callable, List

import dashscope
from dashscope import MultiModalConversation, Generation
from dashscope.audio.tts_v2 import SpeechSynthesizer, ResultCallback
from http import HTTPStatus

from .tts_callbacks import FileWriterCallback

logger = logging.getLogger(__name__)

class AliyunAPIService:
    """封装阿里云API（ASR、TTS）的调用服务"""
    
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
    
    def recognize_audio(self, audio_url: str, prompt: Optional[str] = None) -> str:
        """
        调用阿里云Qwen-Audio多模态大模型进行语音理解和识别。
        该模型不仅能进行语音转文字(ASR)，还能根据可选的文本提示(prompt)进行互动。
        
        Args:
            audio_url: 音频文件的URL
            prompt: 可选的文本提示，用于引导模型的语音理解和互动。例如："这段音频在说什么？"
            
        Returns:
            str: 模型对语音的理解结果或识别出的文本
            
        Raises:
            Exception: 如果API调用失败
        """
        try:
            # 构建messages请求参数
            content = [{"audio": audio_url}]
            if prompt:
                content.append({"text": prompt})
            
            messages = [
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            # 调用Qwen-Audio API
            response = MultiModalConversation.call(
                model="qwen-audio-turbo-latest", 
                messages=messages,
                result_format="message"
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"ASR调用失败: Code={response.code}, Message={response.message}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # 从响应中提取文本
            recognized_text = ""
            if response.output and response.output.choices:
                for content_item in response.output.choices[0].message.content:
                    if "text" in content_item:
                        recognized_text += content_item["text"]
            
            logger.info(f"Qwen-Audio处理成功: {recognized_text[:50]}...")
            return recognized_text
            
        except Exception as e:
            logger.error(f"语音识别过程中发生错误: {str(e)}")
            raise
    
    def synthesize_speech(self, text: str, voice_id: Optional[str] = None) -> str:
        """
        调用阿里云CosyVoice进行文本转语音(TTS)，使用同步方式
        
        Args:
            text: 要转换为语音的文本
            voice_id: 音色ID，如果不提供则使用默认音色
            
        Returns:
            str: 生成的音频文件的URL或路径
            
        Raises:
            Exception: 如果API调用失败
        """
        try:
            # 如果未指定音色，使用默认音色
            voice = voice_id or "longxiaochun_v2"
            
            # 实例化语音合成器
            synthesizer = SpeechSynthesizer(
                model="cosyvoice-v2",
                voice=voice
            )
            
            # 调用CosyVoice API
            audio_data = synthesizer.call(text)
            
            # 为语音结果生成一个唯一的文件名
            import uuid
            import datetime
            import os
            
            unique_id = str(uuid.uuid4())
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"tts_{timestamp}_{unique_id}.mp3"
            
            # 保存音频文件到临时目录
            # 需要确保这个目录存在并且可写
            tmp_dir = os.environ.get('TMP_DIR', 'tmp/audio')
            os.makedirs(tmp_dir, exist_ok=True)
            
            output_path = os.path.join(tmp_dir, filename)
            with open(output_path, 'wb') as f:
                f.write(audio_data)
            
            # 构建文件URL
            # 注：此处假设有一个基础URL可以访问临时文件
            # 实际应用中，需要根据您的文件服务配置正确的URL
            base_url = os.environ.get('BASE_URL', '')
            file_url = f"{base_url}/tmp/audio/{filename}"
            
            logger.info(f"语音合成成功，文件保存为: {output_path}")
            return file_url
            
        except Exception as e:
            logger.error(f"语音合成过程中发生错误: {str(e)}")
            raise

    def synthesize_speech_async(self, 
                               text: str, 
                               voice_id: Optional[str] = None, 
                               on_complete: Optional[Callable[[str], None]] = None,
                               on_error: Optional[Callable[[str], None]] = None) -> None:
        """
        调用阿里云CosyVoice进行文本转语音(TTS)，使用异步方式
        
        Args:
            text: 要转换为语音的文本
            voice_id: 音色ID，如果不提供则使用默认音色
            on_complete: 当语音合成完成时的回调函数，参数为生成的音频文件URL
            on_error: 当语音合成出错时的回调函数，参数为错误信息
            
        Raises:
            Exception: 如果API调用失败
        """
        try:
            # 如果未指定音色，使用默认音色
            voice = voice_id or "longxiaochun_v2"
            
            # 创建文件写入回调
            file_writer = FileWriterCallback(
                on_complete_callback=on_complete,
                on_error_callback=on_error
            )
            
            # 实例化语音合成器
            synthesizer = SpeechSynthesizer(
                model="cosyvoice-v2",
                voice=voice,
                callback=file_writer
            )
            
            # 调用CosyVoice API
            synthesizer.call(text)
            
            logger.info("语音合成异步请求已提交")
            
        except Exception as e:
            logger.error(f"提交语音合成异步请求时发生错误: {str(e)}")
            # 如果初始化或提交过程中出错，调用错误回调
            if on_error:
                on_error(str(e))
            raise

    def synthesize_speech_streaming(self, text: str, voice_id: Optional[str] = None, callback: Optional[ResultCallback] = None) -> None:
        """
        调用阿里云CosyVoice进行文本转语音(TTS)，使用流式处理方式
        
        Args:
            text: 要转换为语音的文本
            voice_id: 音色ID，如果不提供则使用默认音色
            callback: 回调接口，用于处理流式接收到的音频数据
            
        Raises:
            Exception: 如果API调用失败
        """
        if not callback:
            raise ValueError("必须提供callback参数来处理流式音频数据")
            
        try:
            # 如果未指定音色，使用默认音色
            voice = voice_id or "longxiaochun_v2"
            
            # 实例化语音合成器
            synthesizer = SpeechSynthesizer(
                model="cosyvoice-v2",
                voice=voice,
                callback=callback
            )
            
            # 调用CosyVoice API
            synthesizer.call(text)
            
            logger.info("语音合成流已启动，结果将通过回调函数处理")
            
        except Exception as e:
            logger.error(f"语音合成流处理中发生错误: {str(e)}")
            raise
            
    def stream_llm_with_tts(self, 
                           prompt: str, 
                           system_prompt: Optional[str] = None,
                           voice_id: Optional[str] = None,
                           llm_model: str = "qwen-turbo",
                           tts_model: str = "cosyvoice-v2",
                           on_text_chunk: Optional[Callable[[str], None]] = None,
                           on_audio_chunk: Optional[Callable[[bytes], None]] = None,
                           on_error: Optional[Callable[[str], None]] = None,
                           on_complete: Optional[Callable[[], None]] = None) -> None:
        """
        调用大语言模型生成回复并实时进行语音合成，实现低延迟的语音交互。
        LLM生成的文本会以流式方式输出，每个文本块立即传递给TTS进行实时语音合成。
        
        Args:
            prompt: 用户输入的问题或指令
            system_prompt: 系统提示，用于引导大语言模型的行为，如果不提供则使用默认值
            voice_id: 语音合成使用的音色ID，如果不提供则使用默认音色
            llm_model: 使用的大语言模型，默认为"qwen-turbo"
            tts_model: 使用的语音合成模型，默认为"cosyvoice-v2"
            on_text_chunk: 当接收到一个新的文本块时调用的回调函数
            on_audio_chunk: 当接收到一个新的音频数据块时调用的回调函数
            on_error: 当处理过程中发生错误时调用的回调函数
            on_complete: 当整个处理过程完成时调用的回调函数
            
        Raises:
            Exception: 如果API调用失败
        """
        try:
            # 如果未指定系统提示，使用默认提示
            if not system_prompt:
                system_prompt = '你是一个友善、有帮助的AI助手。请用简洁明了的语言回答用户的问题。'
            
            # 如果未指定音色，使用默认音色
            voice = voice_id or "longxiaochun_v2"
            
            # 定义TTS回调处理类
            class StreamCallback(ResultCallback):
                def on_open(self):
                    logger.debug("TTS WebSocket连接已打开")
                
                def on_complete(self):
                    logger.debug("TTS语音合成任务完成")
                
                def on_error(self, message: str):
                    logger.error(f"TTS语音合成任务失败: {message}")
                    if on_error:
                        on_error(f"TTS错误: {message}")
                
                def on_close(self):
                    logger.debug("TTS WebSocket连接已关闭")
                
                def on_event(self, message):
                    logger.debug(f"TTS事件: {message}")
                
                def on_data(self, data: bytes) -> None:
                    if on_audio_chunk:
                        on_audio_chunk(data)
            
            # 初始化TTS合成器
            synthesizer = SpeechSynthesizer(
                model=tts_model,
                voice=voice,
                callback=StreamCallback()
            )
            
            # 准备LLM调用
            messages = []
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            # 调用LLM并处理流式响应
            logger.info(f"开始调用LLM ({llm_model}) 和实时TTS...")
            responses = Generation.call(
                model=llm_model,
                messages=messages,
                result_format='message',  # 设置结果格式为'message'
                stream=True,              # 启用流式输出
                incremental_output=True,  # 启用增量输出
            )
            
            full_text = ""
            for response in responses:
                if response.status_code == HTTPStatus.OK:
                    # 获取LLM生成的文本块
                    if 'choices' in response.output and len(response.output.choices) > 0:
                        llm_chunk = response.output.choices[0].get('message', {}).get('content', '')
                        
                        if llm_chunk:
                            full_text += llm_chunk
                            logger.debug(f"收到LLM文本块: {llm_chunk}")
                            
                            # 调用文本块回调函数
                            if on_text_chunk:
                                on_text_chunk(llm_chunk)
                            
                            # 将LLM文本块发送给TTS进行实时合成
                            synthesizer.streaming_call(llm_chunk)
                else:
                    error_msg = f"LLM调用失败: RequestID={response.request_id}, StatusCode={response.status_code}, ErrorCode={response.code}, Message={response.message}"
                    logger.error(error_msg)
                    if on_error:
                        on_error(error_msg)
                    break
            
            # 完成流式TTS处理
            synthesizer.streaming_complete()
            logger.info(f"LLM和TTS流式处理完成，共生成文本: {len(full_text)} 字符")
            
            # 调用完成回调
            if on_complete:
                on_complete()
                
        except Exception as e:
            error_msg = f"流式LLM-TTS处理过程中发生错误: {str(e)}"
            logger.error(error_msg)
            if on_error:
                on_error(error_msg)
            raise 