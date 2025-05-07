#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import redis
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

class RedisReporter:
    """Redis报告器，用于上报任务进度和结果"""
    
    def __init__(self, redis_host: str, redis_port: int, redis_db: int, 
                 progress_channel: str, redis_password: Optional[str] = None):
        """初始化Redis报告器
        
        Args:
            redis_host: Redis主机地址
            redis_port: Redis端口
            redis_db: Redis数据库编号
            progress_channel: 进度通道名称
            redis_password: Redis密码（可选）
        """
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )
        self.progress_channel = progress_channel
        logger.info(f"Redis报告器初始化完成，进度通道: {progress_channel}")
    
    def report_status(self, task_id: str, session_id: str, status: str, 
                      message: str = None) -> bool:
        """上报任务状态
        
        Args:
            task_id: 任务ID
            session_id: 会话ID
            status: 状态（例如：'processing', 'completed', 'error'）
            message: 状态消息（可选）
            
        Returns:
            bool: 是否上报成功
        """
        try:
            data = {
                'task_id': task_id,
                'session_id': session_id,
                'status': status
            }
            
            if message:
                data['message'] = message
                
            self.redis_client.publish(
                self.progress_channel,
                json.dumps(data)
            )
            logger.debug(f"状态上报成功: {status} - {task_id}")
            return True
        except Exception as e:
            logger.error(f"状态上报失败: {str(e)}")
            return False
    
    def report_progress(self, task_id: str, session_id: str, percentage: float, 
                       message: Optional[str] = None) -> bool:
        """上报任务进度
        
        Args:
            task_id: 任务ID
            session_id: 会话ID
            percentage: 进度百分比（0-100）
            message: 进度消息（可选）
            
        Returns:
            bool: 是否上报成功
        """
        try:
            data = {
                'task_id': task_id,
                'session_id': session_id,
                'status': 'progress',
                'percentage': percentage
            }
            
            if message:
                data['message'] = message
                
            self.redis_client.publish(
                self.progress_channel,
                json.dumps(data)
            )
            logger.debug(f"进度上报成功: {percentage}% - {task_id}")
            return True
        except Exception as e:
            logger.error(f"进度上报失败: {str(e)}")
            return False
    
    def report_completion(self, task_id: str, session_id: str, video_url: str, 
                         message: Optional[str] = None) -> bool:
        """上报任务完成
        
        Args:
            task_id: 任务ID
            session_id: 会话ID
            video_url: 生成视频的URL
            message: 完成消息（可选）
            
        Returns:
            bool: 是否上报成功
        """
        try:
            data = {
                'task_id': task_id,
                'session_id': session_id,
                'status': 'completed',
                'video_url': video_url
            }
            
            if message:
                data['message'] = message
                
            self.redis_client.publish(
                self.progress_channel,
                json.dumps(data)
            )
            logger.info(f"完成上报成功: {task_id} - {video_url}")
            return True
        except Exception as e:
            logger.error(f"完成上报失败: {str(e)}")
            return False
    
    def report_error(self, task_id: str, session_id: str, error_message: str) -> bool:
        """上报任务错误
        
        Args:
            task_id: 任务ID
            session_id: 会话ID
            error_message: 错误消息
            
        Returns:
            bool: 是否上报成功
        """
        try:
            data = {
                'task_id': task_id,
                'session_id': session_id,
                'status': 'error',
                'error': error_message
            }
                
            self.redis_client.publish(
                self.progress_channel,
                json.dumps(data)
            )
            logger.error(f"错误上报: {task_id} - {error_message}")
            return True
        except Exception as e:
            logger.error(f"错误上报失败: {str(e)}")
            return False
    
    def update_gpu_status(self, gpu_status_key: str, status: str) -> bool:
        """更新GPU状态
        
        Args:
            gpu_status_key: GPU状态键名
            status: 状态值（'idle'或'busy'）
            
        Returns:
            bool: 是否更新成功
        """
        try:
            self.redis_client.set(gpu_status_key, status)
            logger.debug(f"GPU状态更新: {gpu_status_key} = {status}")
            return True
        except Exception as e:
            logger.error(f"GPU状态更新失败: {str(e)}")
            return False 