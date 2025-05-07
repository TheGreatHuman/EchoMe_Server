#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from typing import Dict, Any

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkerConfig:
    """Worker配置类"""
    
    def __init__(self):
        """初始化Worker配置"""
        # Redis连接配置
        self.redis_host = os.environ.get('REDIS_HOST', 'localhost')
        self.redis_port = int(os.environ.get('REDIS_PORT', 6379))
        self.redis_db = int(os.environ.get('REDIS_DB', 0))
        self.redis_password = os.environ.get('REDIS_PASSWORD', None)
        
        # GPU设备配置
        self.gpu_id = int(os.environ.get('GPU_ID', 0))
        self.device = f"cuda:{self.gpu_id}" if os.environ.get('DEVICE', 'cuda') == 'cuda' else 'cpu'
        
        # 任务队列名称
        self.task_queue_name = os.environ.get('TASK_QUEUE_NAME', f'task_queue_gpu_{self.gpu_id}')
        
        # GPU状态键
        self.gpu_status_key = f'gpu_status:{self.gpu_id}'
        
        # Redis进度通道
        self.progress_channel = os.environ.get('PROGRESS_CHANNEL', 'task_progress')
        
        # 临时文件目录
        self.temp_dir = os.environ.get('TEMP_DIR', 'temp')
        
        # 输出视频目录
        self.output_dir = os.environ.get('OUTPUT_DIR', 'output')
        
        # 模型加载配置
        self.load_models = os.environ.get('LOAD_MODELS', 'true').lower() == 'true'
        
        # 权重文件路径配置
        self.pretrained_weights_dir = os.environ.get('PRETRAINED_WEIGHTS_DIR', 'pretrained_weights')
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "redis_db": self.redis_db,
            "gpu_id": self.gpu_id,
            "device": self.device,
            "task_queue_name": self.task_queue_name,
            "gpu_status_key": self.gpu_status_key,
            "progress_channel": self.progress_channel,
            "temp_dir": self.temp_dir,
            "output_dir": self.output_dir,
            "load_models": self.load_models,
            "pretrained_weights_dir": self.pretrained_weights_dir
        } 