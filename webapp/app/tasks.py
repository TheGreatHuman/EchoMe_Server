#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import uuid
from typing import Dict, Any, Optional
import redis
from flask import current_app

logger = logging.getLogger(__name__)

class TaskSubmitter:
    """
    任务提交器，负责将任务发送到指定的队列
    """
    
    def __init__(self):
        """初始化任务提交器"""
        # 从配置获取Redis连接信息
        redis_host = current_app.config.get('REDIS_HOST', 'localhost')
        redis_port = current_app.config.get('REDIS_PORT', 6379)
        redis_db = current_app.config.get('REDIS_DB', 0)
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        
        # 任务队列通道前缀
        self.pubsub_channel = current_app.config.get('PUBSUB_CHANNEL', 'task_events')
    
    def submit_task(self, queue_name: str, task_data: Dict[str, Any]) -> bool:
        """
        提交任务到指定队列
        
        Args:
            queue_name: 队列名称
            task_data: 任务数据
            
        Returns:
            bool: 是否提交成功
        """
        try:
            # 确保任务ID
            if 'task_id' not in task_data:
                task_data['task_id'] = str(uuid.uuid4())
            
            # 序列化任务数据
            task_json = json.dumps(task_data)
            
            # 发送到Redis列表
            self.redis_client.lpush(queue_name, task_json)
            
            # 通过Pub/Sub通知任务已提交
            self.redis_client.publish(
                self.pubsub_channel,
                json.dumps({
                    'event': 'task_submitted',
                    'task_id': task_data['task_id'],
                    'queue': queue_name
                })
            )
            
            logger.info(f"任务已提交到队列 {queue_name}: {task_data['task_id']}")
            return True
            
        except Exception as e:
            logger.exception(f"提交任务时出错: {str(e)}")
            return False
    
    def task_exists(self, task_id: str) -> bool:
        """
        检查任务是否存在于任何队列
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 任务是否存在
        """
        try:
            # 这个实现比较简单，实际上需要遍历所有队列或使用其他数据结构
            # 如Redis的Sets来跟踪任务ID
            return False
            
        except Exception as e:
            logger.exception(f"检查任务是否存在时出错: {str(e)}")
            return False

# 创建全局实例
task_submitter = TaskSubmitter()

def submit_task_to_worker(queue_name: str, task_data: Dict[str, Any]) -> bool:
    """
    将任务提交到Worker队列
    
    Args:
        queue_name: 队列名称
        task_data: 任务数据
        
    Returns:
        bool: 是否提交成功
    """
    return task_submitter.submit_task(queue_name, task_data) 