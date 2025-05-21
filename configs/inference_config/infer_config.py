#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：EchoMimic
@File    ：echo_mimic_config.py
@Author  ：
@Date    ：2024 
'''
import os
from omegaconf import OmegaConf
from pathlib import Path
from torch import float16, float32

# 获取 infer_config.py 文件所在的目录
# Path(__file__) -> 获取当前文件的绝对路径
# .resolve() -> 解析任何符号链接，得到规范路径
# .parent -> 获取父目录
CURRENT_DIR = Path(__file__).resolve().parent  # 指向 configs/inference_config/
CONFIG_ROOT_DIR = CURRENT_DIR.parent           # 指向 configs/
PROJECT_ROOT_DIR = CONFIG_ROOT_DIR.parent  

class InferenceConfig:
    """EchoMimic模型推理配置类"""
    
    # 默认配置
    DEFAULT_MODEL_CONFIG = CURRENT_DIR / "animation_acc.yaml"
    DEFAULT_INFER_CONFIG = CURRENT_DIR / "inference_v2.yaml"
    DEFAULT_WIDTH = 512
    DEFAULT_HEIGHT = 512
    DEFAULT_LENGTH = 1200
    DEFAULT_SEED = 420
    DEFAULT_FACEMUSK_DILATION_RATIO = 0.1
    DEFAULT_FACECROP_DILATION_RATIO = 0.5
    
    DEFAULT_CONTEXT_FRAMES = 12
    DEFAULT_CONTEXT_OVERLAP = 3
    
    DEFAULT_CFG = 1.0
    DEFAULT_STEPS = 5
    DEFAULT_SAMPLE_RATE = 16000
    DEFAULT_FPS = 24
    DEFAULT_DEVICE = "cuda"
    
    def __init__(self, config_path=None):
        """初始化EchoMimic配置
        
        Args:
            config_path: 配置文件路径，如果提供，将从文件加载配置
        """
        # 设置默认值
        self.width: int = self.DEFAULT_WIDTH
        self.height: int = self.DEFAULT_HEIGHT
        self.length: int = self.DEFAULT_LENGTH
        self.seed: int = self.DEFAULT_SEED
        self.facemusk_dilation_ratio: float = self.DEFAULT_FACEMUSK_DILATION_RATIO
        self.facecrop_dilation_ratio: float = self.DEFAULT_FACECROP_DILATION_RATIO
        
        self.context_frames: int = self.DEFAULT_CONTEXT_FRAMES
        self.context_overlap: int = self.DEFAULT_CONTEXT_OVERLAP
        
        self.cfg: float = self.DEFAULT_CFG
        self.steps: int = self.DEFAULT_STEPS
        self.sample_rate: int = self.DEFAULT_SAMPLE_RATE
        self.fps: int = self.DEFAULT_FPS
        self.device: str = self.DEFAULT_DEVICE

        self.model_configs = OmegaConf.load(self.DEFAULT_MODEL_CONFIG)

        self.infer_configs = OmegaConf.load(self.DEFAULT_INFER_CONFIG)

        self.weight_dtype = float16 if self.model_configs.weight_dtype == "fp16" else float32

    
    def to_dict(self):
        """将配置转换为字典
        
        Returns:
            dict: 包含配置参数的字典
        """
        return {
            "width": self.width,
            "height": self.height,
            "length": self.length,
            "seed": self.seed,
            "facemusk_dilation_ratio": self.facemusk_dilation_ratio,
            "facecrop_dilation_ratio": self.facecrop_dilation_ratio,
            "context_frames": self.context_frames,
            "context_overlap": self.context_overlap,
            "cfg": self.cfg,
            "steps": self.steps,
            "sample_rate": self.sample_rate,
            "fps": self.fps,
            "device": self.device
        } 