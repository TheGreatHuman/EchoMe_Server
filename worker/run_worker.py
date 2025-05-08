#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import argparse
import time
import signal
import json
from pathlib import Path

import torch
from omegaconf import OmegaConf


# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 获取上一级目录
parent_dir = os.path.dirname(current_dir)
# print(parent_dir)

# 将上一级目录添加到sys.path
sys.path.append(parent_dir)

from config import WorkerConfig
from worker.redis_reporter import RedisReporter
from worker.tasks import ModelManager, TaskProcessor, TaskConsumer
from configs.inference_config import InferenceConfig

from dotenv import load_dotenv


# 加载环境变量
load_dotenv()

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
task_consumer = None


def signal_handler(sig, frame):
    """处理终止信号"""
    logger.info("接收到终止信号，准备退出...")
    if task_consumer:
        task_consumer.stop()
    sys.exit(0)


def main():
    """Worker主函数"""
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='EchoMimic Worker')
    parser.add_argument('--gpu-id', type=int, default=None, help='GPU ID (默认为环境变量或0)')
    parser.add_argument('--redis-host', type=str, default=None, help='Redis主机地址')
    parser.add_argument('--redis-port', type=int, default=None, help='Redis端口')
    parser.add_argument('--queue-name', type=str, default=None, help='任务队列名称')
    parser.add_argument('--no-load-models', action='store_true', help='不加载模型(用于测试)')
    args = parser.parse_args()
    
    # 加载Worker配置
    config = WorkerConfig()
    
    # 命令行参数覆盖环境变量
    if args.gpu_id is not None:
        os.environ['GPU_ID'] = str(args.gpu_id)
        config.gpu_id = args.gpu_id
        config.device = f"cuda:{args.gpu_id}" if torch.cuda.is_available() else 'cpu'
    
    if args.redis_host:
        config.redis_host = args.redis_host
    
    if args.redis_port:
        config.redis_port = args.redis_port
    
    if args.queue_name:
        config.task_queue_name = args.queue_name
    
    if args.no_load_models:
        config.load_models = False
    
    # 检查CUDA是否可用
    if not torch.cuda.is_available() and 'cuda' in config.device:
        logger.error("CUDA不可用，但指定了CUDA设备！")
        config.device = 'cpu'
        logger.warning("已切换到CPU模式，性能可能受到显著影响")
    
    logger.info(f"Worker配置: GPU={config.gpu_id}, 设备={config.device}, Redis={config.redis_host}:{config.redis_port}")
    logger.info(f"任务队列: {config.task_queue_name}, 状态键: {config.gpu_status_key}")
    
    # 初始化Redis报告器
    reporter = RedisReporter(
        redis_host=config.redis_host,
        redis_port=config.redis_port,
        redis_db=config.redis_db,
        progress_channel=config.progress_channel,
        redis_password=config.redis_password
    )
    
    # 加载推理配置
    inference_config = InferenceConfig()
    # print(type(inference_config))
    
    # 初始化模型管理器
    model_manager = ModelManager(
        device=config.device, 
        config=inference_config,
        model_base_dir = parent_dir
    )
    
    # 加载模型
    if config.load_models:
        logger.info("开始加载模型...")
        if not model_manager.load_models():
            logger.error("模型加载失败，Worker无法启动")
            sys.exit(1)
    else:
        logger.warning("跳过模型加载")
    
    # 创建目录
    os.makedirs(config.temp_dir, exist_ok=True)
    os.makedirs(config.output_dir, exist_ok=True)
    
    # 初始化任务处理器
    task_processor = TaskProcessor(
        model_manager=model_manager,
        reporter=reporter,
        temp_dir=config.temp_dir,
        output_dir=config.output_dir,
        config=inference_config
    )
    
    # 初始化任务消费者
    global task_consumer
    task_consumer = TaskConsumer(
        redis_config={
            'redis_host': config.redis_host,
            'redis_port': config.redis_port,
            'redis_db': config.redis_db,
            'redis_password': config.redis_password
        },
        task_processor=task_processor,
        gpu_status_key=config.gpu_status_key,
        task_queue_name=config.task_queue_name,
        reporter=reporter
    )
    
    # 启动任务消费者
    logger.info("启动任务消费者...")
    task_consumer.start()
    
    # 标记Worker就绪
    reporter.update_gpu_status(config.gpu_status_key, 'idle')
    logger.info(f"Worker已就绪，监听任务队列: {config.task_queue_name}")
    
    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("接收到键盘中断，准备退出...")
    finally:
        if task_consumer:
            task_consumer.stop()


if __name__ == '__main__':
    main() 