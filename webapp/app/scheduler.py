#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import random
from typing import Optional, List, Dict
import redis
from flask import current_app

logger = logging.getLogger(__name__)

class Scheduler:
    """
    任务调度器，负责选择一个可用的Worker队列
    
    调度策略：
    1. 轮询（Round Robin）：依次选择下一个Worker
    2. 负载均衡：选择当前负载最低的Worker
    3. 随机选择：随机选择一个空闲Worker
    """
    
    def __init__(self):
        """初始化调度器"""
        # 从配置获取Redis连接信息
        redis_host = current_app.config.get('REDIS_HOST', 'localhost')
        redis_port = current_app.config.get('REDIS_PORT', 6379)
        redis_db = current_app.config.get('REDIS_DB', 0)
        redis_pass = current_app.config.get('REDIS_PASSWORD')
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, password=redis_pass)
        
        # 队列名前缀和最大Worker数量
        self.task_queue_prefix = current_app.config.get('TASK_QUEUE_PREFIX', 'task_queue_gpu_')
        self.max_workers = current_app.config.get('MAX_WORKERS', 2)
        
        # Worker状态键前缀
        self.gpu_status_prefix = current_app.config.get('GPU_STATUS_PREFIX', 'gpu_status:')
        
        # 上次选择的Worker索引（用于轮询）
        self.last_selected_index = -1
        
        # 调度策略
        self.strategy = current_app.config.get('SCHEDULER_STRATEGY', 'load_balance')
    
    def get_worker_status(self, worker_id: int) -> str:
        """
        获取指定Worker的状态
        
        Args:
            worker_id: Worker ID
            
        Returns:
            str: Worker状态 ('idle'|'busy'|'offline')
        """
        try:
            status_key = f"{self.gpu_status_prefix}{worker_id}"
            status = self.redis_client.get(status_key)
            
            if status is None:
                return 'offline'
            
            return status.decode('utf-8')
            
        except Exception as e:
            logger.exception(f"获取Worker状态时出错: {str(e)}")
            return 'offline'
    
    def get_all_worker_statuses(self) -> Dict[int, str]:
        """
        获取所有Worker的状态
        
        Returns:
            Dict[int, str]: {worker_id: status}
        """
        statuses = {}
        
        for worker_id in range(self.max_workers):
            statuses[worker_id] = self.get_worker_status(worker_id)
        
        return statuses
    
    def get_idle_workers(self) -> List[int]:
        """
        获取所有空闲的Worker
        
        Returns:
            List[int]: 空闲Worker ID列表
        """
        idle_workers = []
        
        for worker_id in range(self.max_workers):
            if self.get_worker_status(worker_id) == 'idle':
                idle_workers.append(worker_id)
        
        return idle_workers
    
    def select_worker_queue(self) -> Optional[str]:
        """
        选择一个Worker队列
        
        Returns:
            Optional[str]: 队列名或None（如果没有可用Worker）
        """
        idle_workers = self.get_idle_workers()
        
        if not idle_workers:
            logger.warning("没有可用的Worker")
            return None
        
        selected_worker_id = None
        
        # 根据策略选择Worker
        if self.strategy == 'round_robin':
            # 轮询策略
            self.last_selected_index = (self.last_selected_index + 1) % len(idle_workers)
            selected_worker_id = idle_workers[self.last_selected_index]
            
        elif self.strategy == 'random':
            # 随机策略
            selected_worker_id = random.choice(idle_workers)
            
        else:
            # 默认：负载均衡策略
            # 在当前实现中，所有idle的worker负载都是0，所以直接选第一个
            selected_worker_id = idle_workers[0]
        
        logger.info(f"已选择Worker: {selected_worker_id}")
        return f"{self.task_queue_prefix}{selected_worker_id}" 