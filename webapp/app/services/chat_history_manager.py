#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import uuid

import dashscope
from dashscope import MultiModalConversation

from app import db
from app.models.message_model import Message
from app.models.conversation_model import Conversation

logger = logging.getLogger(__name__)

class ChatHistoryManager:
    """
    聊天记录管理类，用于：
    1. 记录用户会话中的语音、文本消息
    2. 在会话结束时调用Qwen-Audio总结对话内容
    3. 将总结内容持久化到数据库
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化聊天记录管理器
        
        Args:
            api_key: 阿里云DashScope API Key，如果不提供则从环境变量获取
        """
        # 从环境变量获取API Key或使用传入的API Key
        self.api_key = api_key or os.environ.get('DASHSCOPE_API_KEY')
        
        if not self.api_key:
            logger.warning("未提供DASHSCOPE_API_KEY，API调用将可能失败")
        else:
            dashscope.api_key = self.api_key
            
        # 保存会话历史记录的字典，键为会话ID，值为消息列表
        self.session_histories = {}
        
    def _get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取指定会话的历史记录
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict[str, Any]]: 会话历史记录列表
        """
        if session_id not in self.session_histories:
            self.session_histories[session_id] = []
        
        return self.session_histories[session_id]
    
    def add_user_audio(self, session_id: str, audio_url: str) -> None:
        """
        添加用户音频消息到会话历史记录
        
        Args:
            session_id: 会话ID
            audio_url: 音频URL
        """
        history = self._get_history(session_id)
        
        # 添加用户音频消息
        history.append({
            "role": "user",
            "content": [{"audio": audio_url}],
            "timestamp": datetime.utcnow().isoformat(),
            "type": "audio"
        })
        
        logger.debug(f"添加用户音频到会话 {session_id}: {audio_url}")
    
    def add_user_text(self, session_id: str, text: str) -> None:
        """
        添加用户文本消息到会话历史记录
        
        Args:
            session_id: 会话ID
            text: 用户文本消息
        """
        history = self._get_history(session_id)
        
        # 添加用户文本消息
        history.append({
            "role": "user",
            "content": [{"text": text}],
            "timestamp": datetime.utcnow().isoformat(),
            "type": "text"
        })
        
        logger.debug(f"添加用户文本到会话 {session_id}: {text[:50]}...")
    
    def add_ai_response(self, session_id: str, text: str, audio_url: Optional[str] = None) -> None:
        """
        添加AI回复到会话历史记录
        
        Args:
            session_id: 会话ID
            text: AI文本回复
            audio_url: 可选的AI语音回复URL
        """
        history = self._get_history(session_id)
        
        # 准备AI回复内容
        content = [{"text": text}]
        content_type = "text"
        
        if audio_url:
            content.append({"audio": audio_url})
            content_type = "audio"
        
        # 添加AI回复
        history.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "type": content_type
        })
        
        logger.debug(f"添加AI回复到会话 {session_id}: {text[:50]}...")
    
    def convert_history_to_dashscope_format(self, session_id: str) -> List[Dict[str, Any]]:
        """
        将内部历史记录格式转换为DashScope API所需的格式
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict[str, Any]]: DashScope格式的消息历史
        """
        history = self._get_history(session_id)
        dashscope_messages = []
        
        for msg in history:
            dashscope_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return dashscope_messages
    
    def get_recent_messages(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的消息记录
        
        Args:
            session_id: 会话ID
            limit: 最大消息数量
            
        Returns:
            List[Dict[str, Any]]: 最近的消息记录
        """
        history = self._get_history(session_id)
        return history[-limit:] if history else []
    
    def clear_history(self, session_id: str) -> None:
        """
        清除指定会话的历史记录
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.session_histories:
            del self.session_histories[session_id]
            logger.info(f"已清除会话 {session_id} 的历史记录")
    
    def summarize_conversation(self, session_id: str, conversation_id: str) -> Optional[str]:
        """
        总结指定会话的对话内容，并将结果保存到数据库
        
        Args:
            session_id: 会话ID
            conversation_id: 数据库中的对话ID
            
        Returns:
            Optional[str]: 总结内容，如果失败则返回None
        """
        history = self._get_history(session_id)
        
        if not history:
            logger.warning(f"会话 {session_id} 没有历史记录，无法总结")
            return None
        
        try:
            # 构建用于总结的消息列表
            dashscope_messages = self.convert_history_to_dashscope_format(session_id)
            
            # 添加系统提示，引导模型生成总结
            dashscope_messages.insert(0, {
                "role": "system",
                "content": [{"text": "请总结一下这段对话的内容。要求简明扼要，抓住重点，不超过150字。"}]
            })
            
            # 调用Qwen-Audio API生成总结
            response = MultiModalConversation.call(
                model="qwen-audio-turbo-latest",
                messages=dashscope_messages,
                result_format="message"
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"总结对话失败: Code={response.code}, Message={response.message}"
                logger.error(error_msg)
                return None
            
            # 提取总结文本
            summary = ""
            if response.output and response.output.choices:
                for content_item in response.output.choices[0].message.content:
                    if "text" in content_item:
                        summary += content_item["text"]
            
            if not summary:
                logger.error("无法从API响应中提取总结文本")
                return None
            
            # 将总结保存到数据库中的conversation和message
            self._save_summary_to_database(conversation_id, summary)
            
            logger.info(f"已生成会话 {session_id} 的总结并保存到数据库")
            return summary
            
        except Exception as e:
            logger.exception(f"总结对话过程中发生错误: {str(e)}")
            return None
    
    def _save_summary_to_database(self, conversation_id: str, summary: str) -> None:
        """
        将总结内容保存到数据库
        
        Args:
            conversation_id: 对话ID
            summary: 总结内容
        """
        try:
            # 更新Conversation表的last_message字段
            conversation = Conversation.query.filter_by(
                conversation_id=uuid.UUID(conversation_id).bytes
            ).first()
            
            if not conversation:
                logger.error(f"找不到对话ID为 {conversation_id} 的记录")
                return
            
            # 更新最后消息和时间
            conversation.last_message = summary
            conversation.last_message_time = datetime.utcnow()
            
            # 创建总结消息记录
            summary_message = Message(
                conversation_id=conversation_id,
                type="text",
                content=summary,
                is_user=False,
                end_of_conversation=datetime.utcnow()
            )
            
            # 添加到数据库会话并提交
            db.session.add(summary_message)
            db.session.commit()
            
            logger.debug(f"总结已保存到数据库，对话ID: {conversation_id}")
            
        except Exception as e:
            db.session.rollback()
            logger.exception(f"保存总结到数据库时发生错误: {str(e)}")
    
    def handle_session_end(self, session_id: str, conversation_id: str) -> bool:
        """
        处理会话结束事件，生成总结并保存到数据库，然后清除会话历史记录
        
        Args:
            session_id: 会话ID
            conversation_id: 数据库中的对话ID
            
        Returns:
            bool: 是否成功处理
        """
        try:
            # 生成总结并保存到数据库
            summary = self.summarize_conversation(session_id, conversation_id)
            
            # 清除会话历史记录
            self.clear_history(session_id)
            
            return summary is not None
            
        except Exception as e:
            logger.exception(f"处理会话结束事件时发生错误: {str(e)}")
            return False 