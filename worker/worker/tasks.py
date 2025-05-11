#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import logging
import requests
import random
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Tuple, Union
import threading

import torch
import redis
import numpy as np
import cv2
from PIL import Image
from diffusers import AutoencoderKL, DDIMScheduler
from omegaconf import OmegaConf

from inference.models.unet_2d_condition import UNet2DConditionModel
from inference.models.unet_3d_echo import EchoUNet3DConditionModel
from inference.models.whisper.audio2feature import load_audio_model
from inference.pipelines.pipeline_echo_mimic_acc import Audio2VideoPipeline
from inference.utils.util import save_videos_grid, crop_and_pad
from inference.models.face_locator import FaceLocator
from configs.inference_config import InferenceConfig
from facenet_pytorch import MTCNN

from .redis_reporter import RedisReporter

logger = logging.getLogger(__name__)

class ModelManager:
    """模型管理器，负责加载和管理模型"""
    
    def __init__(self, device: str, config: InferenceConfig, model_base_dir: Path):
        """初始化模型管理器
        
        Args:
            device: 设备（如 'cuda:0'）
            config: 配置信息
        """
        self.device = device
        self.config: InferenceConfig = config
        self.models = {}
        self.weight_dtype = config.weight_dtype
        self.model_base_dir = model_base_dir
        
        logger.info(f"模型管理器初始化成功，设备: {device}")
    
    def load_models(self) -> bool:
        """加载所有需要的模型
        
        Returns:
            bool: 是否加载成功
        """
        try:
            logger.info("开始加载模型...")
            
            # 加载VAE
            logger.info("加载VAE模型...")
            pretrained_vae_path = os.path.join(self.model_base_dir, self.config.model_configs.pretrained_vae_path)
            print(pretrained_vae_path)
            self.models['vae'] = AutoencoderKL.from_pretrained(
                pretrained_vae_path,
            ).to(self.device, dtype=self.weight_dtype)
            
            # 加载参考网络
            logger.info("加载参考网络...")
            pretrained_base_model_path = os.path.join(self.model_base_dir, self.config.model_configs.pretrained_base_model_path)
            reference_unet_path = os.path.join(self.model_base_dir, self.config.model_configs.reference_unet_path)
            reference_unet = UNet2DConditionModel.from_pretrained(
                pretrained_base_model_path,
                subfolder="unet",
            ).to(dtype=self.weight_dtype, device=self.device)
            reference_unet.load_state_dict(
                torch.load(reference_unet_path, map_location="cpu"),
            )
            self.models['reference_unet'] = reference_unet
            
            # 加载去噪网络
            logger.info("加载去噪网络...")
            motion_module_path = os.path.join(self.model_base_dir, self.config.model_configs.motion_module_path)
            if os.path.exists(motion_module_path):
                # stage1 + stage2
                denoising_unet = EchoUNet3DConditionModel.from_pretrained_2d(
                    pretrained_base_model_path,
                    motion_module_path,
                    subfolder="unet",
                    unet_additional_kwargs=self.config.infer_configs.unet_additional_kwargs,
                ).to(dtype=self.weight_dtype, device=self.device)
            else:
                # 仅stage1
                denoising_unet = EchoUNet3DConditionModel.from_pretrained_2d(
                    pretrained_base_model_path,
                    "",
                    subfolder="unet",
                    unet_additional_kwargs={
                        "use_motion_module": False,
                        "unet_use_temporal_attention": False,
                        "cross_attention_dim": self.config.infer_configs.unet_additional_kwargs.cross_attention_dim
                    }
                ).to(dtype=self.weight_dtype, device=self.device)
            denoising_unet_path = os.path.join(self.model_base_dir, self.config.model_configs.denoising_unet_path)
            denoising_unet.load_state_dict(
                torch.load(denoising_unet_path, map_location="cpu"),
                strict=False
            )
            self.models['denoising_unet'] = denoising_unet
            
            # 加载面部定位器
            logger.info("加载面部定位器...")
            face_locator_path = os.path.join(self.model_base_dir, self.config.model_configs.face_locator_path)
            face_locator = FaceLocator(320, conditioning_channels=1, block_out_channels=(16, 32, 96, 256)).to(
                dtype=self.weight_dtype, device=self.device
            )
            face_locator.load_state_dict(torch.load(face_locator_path))
            self.models['face_locator'] = face_locator
            
            # 加载音频处理器
            logger.info("加载音频处理器...")
            audio_model_path = os.path.join(self.model_base_dir, self.config.model_configs.audio_model_path)
            audio_processor = load_audio_model(
                model_path=audio_model_path, 
                device=self.device
            )
            self.models['audio_processor'] = audio_processor
            
            # 加载人脸检测器
            logger.info("加载人脸检测器...")
            face_detector = MTCNN(
                image_size=320, 
                margin=0, 
                min_face_size=20,
                thresholds=[0.6, 0.7, 0.7],
                factor=0.709,
                post_process=True,
                device=self.device
            )
            self.models['face_detector'] = face_detector
            
            # 加载调度器
            logger.info("加载调度器...")
            sched_kwargs = OmegaConf.to_container(self.config.infer_configs.noise_scheduler_kwargs)
            self.models['scheduler'] = DDIMScheduler(**sched_kwargs)
            
            logger.info("所有模型加载完成！")
            return True
        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            logger.error(traceback.format_exc())
            return False
        
    def create_pipeline(self) -> Audio2VideoPipeline:
        """创建推理流水线
        
        Returns:
            Audio2VideoPipeline: 推理流水线
        """
        pipe = Audio2VideoPipeline(
            vae=self.models['vae'],
            reference_unet=self.models['reference_unet'],
            denoising_unet=self.models['denoising_unet'],
            audio_guider=self.models['audio_processor'],
            face_locator=self.models['face_locator'],
            scheduler=self.models['scheduler'],
        )
        pipe = pipe.to(self.device, dtype=self.weight_dtype)
        return pipe
    
    def get_face_detector(self) -> MTCNN:
        """获取人脸检测器
        
        Returns:
            MTCNN: 人脸检测器
        """
        return self.models['face_detector']


def select_face(det_bboxes, probs):
    """从检测到的多个人脸中选择最大的一个
    
    Args:
        det_bboxes: 人脸边界框
        probs: 概率分数
    
    Returns:
        最大人脸的边界框，如果没有合格的人脸则返回None
    """
    # 根据概率筛选
    if det_bboxes is None or probs is None:
        return None
    filtered_bboxes = []
    for bbox_i in range(len(det_bboxes)):
        if probs[bbox_i] > 0.8:
            filtered_bboxes.append(det_bboxes[bbox_i])
    if len(filtered_bboxes) == 0:
        return None

    # 按面积从大到小排序
    sorted_bboxes = sorted(filtered_bboxes, key=lambda x:(x[3]-x[1]) * (x[2] - x[0]), reverse=True)
    return sorted_bboxes[0]


class TaskProcessor:
    """任务处理器，负责处理音频到视频的推理任务"""
    
    def __init__(self, model_manager: ModelManager, reporter: RedisReporter, 
                 temp_dir: str, output_dir: str, config: InferenceConfig):
        """初始化任务处理器
        
        Args:
            model_manager: 模型管理器
            reporter: Redis报告器
            temp_dir: 临时文件目录
            output_dir: 输出视频目录
            config: 配置信息
        """
        self.model_manager = model_manager
        self.reporter = reporter
        self.temp_dir = temp_dir
        self.output_dir = output_dir
        self.config = config
        
        # 创建必要的目录
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info("任务处理器初始化完成")
    
    def download_file(self, url_or_file_id: str, save_path: str) -> bool:
        """下载文件到本地
        
        Args:
            url_or_file_id: 文件URL或文件ID
            save_path: 保存路径
            
        Returns:
            bool: 是否下载成功
        """
        try:
            # 确定基础URL
            base_url = os.environ.get('BASE_URL', 'http://localhost:3000')
            
            # 判断是否为文件ID（不含路径分隔符和http协议前缀）
            if '/' not in url_or_file_id and ':' not in url_or_file_id:
                # 视为文件ID，使用临时文件API下载
                url = f"{base_url}/api/tempfile/download/{url_or_file_id}"
            else:
                # 如果URL是相对路径（如/api/chat/files/xxx.mp3），则添加基础URL
                if url_or_file_id.startswith('/'):
                    url = f"{base_url}{url_or_file_id}"
                else:
                    url = url_or_file_id
            
            # 下载文件
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.debug(f"文件下载成功: {save_path}")
            return True
        except Exception as e:
            logger.error(f"文件下载失败: {str(e)}")
            return False
    
    def upload_file(self, file_path: str) -> Optional[str]:
        """将文件上传到临时文件API
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[str]: 成功时返回文件ID，失败时返回None
        """
        try:
            base_url = os.environ.get('BASE_URL', 'http://localhost:3000')
            upload_url = f"{base_url}/api/tempfile/upload"
            
            # 准备文件数据
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                
                # 上传文件
                response = requests.post(upload_url, files=files)
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                if result.get('success'):
                    file_id = result.get('file_id')
                    logger.info(f"文件上传成功，文件ID: {file_id}")
                    return file_id
                else:
                    logger.error(f"文件上传API返回错误: {result.get('message')}")
                    return None
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            return None
    
    def process_task(self, task_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """处理音频到视频的推理任务
        
        Args:
            task_data: 任务数据，包含任务ID、会话ID、角色图片(文件ID)、音频(文件ID)等
            
        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 临时文件ID)
        """
        try:
            task_id = task_data.get('task_id')
            session_id = task_data.get('session_id')
            ref_image_id = task_data.get('ref_image_id')  # 改为文件ID
            audio_id = task_data.get('audio_id')  # 改为文件ID
            
            # 检查必要参数
            if not all([task_id, session_id, ref_image_id, audio_id]):
                raise ValueError("缺少必要的任务参数")
            
            # 为临时文件生成本地保存路径
            ref_path = os.path.join(self.temp_dir, f"{task_id}_ref_image.jpg")
            audio_path = os.path.join(self.temp_dir, f"{task_id}_audio.wav")
            
            # 下载文件
            self.reporter.report_status(task_id, session_id, 'processing', '下载必要文件...')
            if not self.download_file(ref_image_id, ref_path):
                raise Exception("下载参考图片失败")
            if not self.download_file(audio_id, audio_path):
                raise Exception("下载音频文件失败")
            
            # 人脸处理
            self.reporter.report_progress(task_id, session_id, 10, '处理参考图像...')
            face_img = cv2.imread(ref_path)
            face_mask = np.zeros((face_img.shape[0], face_img.shape[1])).astype('uint8')
            
            # 人脸检测
            face_detector = self.model_manager.get_face_detector()
            det_bboxes, probs = face_detector.detect(face_img)
            select_bbox = select_face(det_bboxes, probs)
            
            if select_bbox is None:
                logger.warning("未检测到合格的人脸，使用整张图像")
                face_mask[:, :] = 255
            else:
                # 根据人脸位置创建面部蒙版
                xyxy = select_bbox[:4]
                xyxy = np.round(xyxy).astype('int')
                rb, re, cb, ce = xyxy[1], xyxy[3], xyxy[0], xyxy[2]
                r_pad = int((re - rb) * self.config.facemusk_dilation_ratio)
                c_pad = int((ce - cb) * self.config.facemusk_dilation_ratio)
                face_mask[rb - r_pad : re + r_pad, cb - c_pad : ce + c_pad] = 255

                # 人脸裁剪
                r_pad_crop = int((re - rb) * self.config.facecrop_dilation_ratio)
                c_pad_crop = int((ce - cb) * self.config.facecrop_dilation_ratio)
                crop_rect = [
                    max(0, cb - c_pad_crop), 
                    max(0, rb - r_pad_crop), 
                    min(ce + c_pad_crop, face_img.shape[1]), 
                    min(re + r_pad_crop, face_img.shape[0])
                ]
                
                face_img, _ = crop_and_pad(face_img, crop_rect)
                face_mask, _ = crop_and_pad(face_mask, crop_rect)
                
                # 调整大小
                face_img = cv2.resize(face_img, (self.config.width, self.config.height))
                face_mask = cv2.resize(face_mask, (self.config.width, self.config.height))
            
            # 将OpenCV图像转换为PIL图像
            ref_image_pil = Image.fromarray(face_img[:, :, [2, 1, 0]])
            
            # 将面部蒙版转换为tensor
            face_mask_tensor = torch.Tensor(face_mask).to(
                dtype=self.model_manager.weight_dtype, 
                device=self.model_manager.device
            ).unsqueeze(0).unsqueeze(0).unsqueeze(0) / 255.0
            
            # 准备推理参数
            width = self.config.width
            height = self.config.height
            length = self.config.length
            steps = self.config.steps
            cfg = self.config.cfg
            context_frames = self.config.context_frames
            context_overlap = self.config.context_overlap
            sample_rate = self.config.sample_rate
            fps = self.config.fps
            seed = self.config.seed
            
            if seed is not None and seed > -1:
                generator = torch.manual_seed(seed)
            else:
                generator = torch.manual_seed(random.randint(100, 1000000))
            
            # 创建推理流水线
            self.reporter.report_progress(task_id, session_id, 15, '创建推理流水线...')
            pipe = self.model_manager.create_pipeline()
            
            # 定义进度回调函数
            last_progress = 15  # 初始进度
            
            def progress_callback(percentage, message=None):
                nonlocal last_progress
                # 将模型内部进度(0-100)映射到整个流程的进度(15-90)
                current_progress = 15 + int(percentage * 0.75)
                if current_progress > last_progress:
                    self.reporter.report_progress(task_id, session_id, current_progress, message)
                    last_progress = current_progress
            
            # 执行推理
            self.reporter.report_progress(task_id, session_id, 20, '开始生成视频...')
            date_str = datetime.now().strftime("%Y%m%d")
            time_str = datetime.now().strftime("%H%M%S")
            
            output_name = f"{ref_image_id.split('.')[0]}_{audio_id.split('.')[0]}_{height}x{width}_{int(cfg)}_{time_str}"
            
            # 创建输出子目录
            save_dir = Path(f"{self.output_dir}/{date_str}/{task_id}_{time_str}")
            save_dir.mkdir(exist_ok=True, parents=True)

            # 实际运行推理
            video = pipe(
                ref_image_pil,
                audio_path,
                face_mask_tensor,
                width,
                height,
                length,
                steps,
                cfg,
                generator=generator,
                audio_sample_rate=sample_rate,
                context_frames=context_frames,
                fps=fps,
                context_overlap=context_overlap,
                callback=progress_callback
            ).videos
            
            # 保存视频
            self.reporter.report_progress(task_id, session_id, 90, '保存视频...')
            output_path = f"{save_dir}/{output_name}.mp4"
            output_path_with_audio = f"{save_dir}/{output_name}_withaudio.mp4"
            
            # 保存无音频视频
            save_videos_grid(video, output_path, n_rows=1, fps=fps)
            
            # 添加音频并保存
            self.reporter.report_progress(task_id, session_id, 95, '添加音频...')
            
            # 使用subprocess添加音频
            success = self._add_audio_to_video(output_path, audio_path, output_path_with_audio)
            
            if not success:
                logger.warning("使用FFmpeg添加音频失败，将返回无音频视频")
                output_path_with_audio = output_path
                
            # 上传视频到临时文件API
            self.reporter.report_progress(task_id, session_id, 98, '上传视频...')
            video_file_id = self.upload_file(output_path_with_audio)
            
            if not video_file_id:
                raise Exception("上传视频失败")
                
            # 清理临时文件
            try:
                os.remove(ref_path)
                os.remove(audio_path)
                os.remove(output_path)
                os.remove(output_path_with_audio) if output_path_with_audio != output_path else None
            except Exception as e:
                logger.warning(f"清理临时文件失败: {str(e)}")
            
            # 清理GPU内存
            torch.cuda.empty_cache()
            
            return True, video_file_id
        except Exception as e:
            logger.error(f"任务处理失败: {str(e)}")
            logger.error(traceback.format_exc())
            self.reporter.report_error(task_data.get('task_id', 'unknown'), task_data.get('session_id', 'unknown'), str(e))
            return False, None
    
    def _add_audio_to_video(self, video_path, audio_path, output_path):
        """使用FFmpeg为视频添加音频
        
        Args:
            video_path: 视频路径
            audio_path: 音频路径
            output_path: 输出路径
            
        Returns:
            bool: 是否成功
        """
        try:
            import subprocess
            
            # FFmpeg命令
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-shortest',
                output_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg错误: {result.stderr}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"添加音频失败: {str(e)}")
            return False


class TaskConsumer:
    """任务消费者，负责从Redis队列中获取任务并处理"""
    
    def __init__(self, redis_config: Dict[str, Any], task_processor: TaskProcessor,
                 gpu_status_key: str, task_queue_name: str, reporter: RedisReporter):
        """初始化任务消费者
        
        Args:
            redis_config: Redis配置
            task_processor: 任务处理器
            gpu_status_key: GPU状态键
            task_queue_name: 任务队列名称
            reporter: Redis报告器
        """
        self.redis_client = redis.Redis(
            host=redis_config.get('redis_host', 'localhost'),
            port=redis_config.get('redis_port', 6379),
            db=redis_config.get('redis_db', 0),
            password=redis_config.get('redis_password')
        )
        self.task_processor = task_processor
        self.gpu_status_key = gpu_status_key
        self.task_queue_name = task_queue_name
        self.reporter = reporter
        self.running = False
        self._thread = None
        
        logger.info(f"任务消费者初始化完成，队列: {task_queue_name}")
    
    def start(self) -> None:
        """启动任务消费者"""
        self.running = True
        self._thread = threading.Thread(target=self._run_consumer)
        self._thread.daemon = True
        self._thread.start()
        
        logger.info(f"任务消费者已启动，监听队列: {self.task_queue_name}")
    
    def stop(self) -> None:
        """停止任务消费者"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("任务消费者已停止")

    def _remove_task_from_set(self, task_id: str) -> bool:
        """
        从集合中移除已完成的任务ID
        
        Args:
            task_id: 要移除的任务ID
            
        Returns:
            bool: 是否成功移除
        """
        try:
            task_set_key = "all_task_ids"
            removed = self.redis_client.srem(task_set_key, task_id)
            if removed:
                logger.info(f"任务ID {task_id} 已从跟踪集合中移除")
            return bool(removed)
        except Exception as e:
            logger.exception(f"从集合中移除任务ID时出错: {str(e)}")
            return False
    
    def _run_consumer(self) -> None:
        """运行任务消费循环"""
        # 设置初始状态为idle
        self.reporter.update_gpu_status(self.gpu_status_key, 'idle')
        
        while self.running:
            try:
                # 阻塞获取任务
                result = self.redis_client.blpop(self.task_queue_name, timeout=1)
                
                if result is None:
                    continue
                    
                # 解析任务数据
                _, task_json = result
                task_data = json.loads(task_json)
                
                task_id = task_data.get('task_id', 'unknown')
                session_id = task_data.get('session_id', 'unknown')
                
                logger.info(f"收到新任务: {task_id}")
                
                # 更新GPU状态为忙碌
                self.reporter.update_gpu_status(self.gpu_status_key, 'busy')
                
                # 处理任务
                success, video_file_id = self.task_processor.process_task(task_data)
                
                # 处理结果
                if success and video_file_id:
                    self.reporter.report_completion(task_id, session_id, video_file_id, '视频生成完成')
                else:
                    self.reporter.report_error(task_id, session_id, '视频生成失败')

                # 移除任务ID
                self._remove_task_from_set(task_id)
            except Exception as e:
                logger.error(f"任务处理过程中出错: {str(e)}")
                logger.error(traceback.format_exc())
            finally:
                # 无论成功失败，都将GPU状态设回idle
                self.reporter.update_gpu_status(self.gpu_status_key, 'idle')
                
                # 清理GPU内存
                torch.cuda.empty_cache() 