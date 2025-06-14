#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：EchoMimic
@File    ：audio2vid.py
@Author  ：juzhen.czy
@Date    ：2024/3/4 17:43 
'''
import argparse
import os

import random
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import torch
from diffusers import AutoencoderKL, DDIMScheduler
from omegaconf import OmegaConf
from PIL import Image

from inference.models.unet_2d_condition import UNet2DConditionModel
from inference.models.unet_3d_echo import EchoUNet3DConditionModel
from inference.models.whisper.audio2feature import load_audio_model
from inference.pipelines.pipeline_echo_mimic_acc import Audio2VideoPipeline
from inference.utils.util import save_videos_grid, crop_and_pad
from inference.models.face_locator import FaceLocator
from moviepy.editor import VideoFileClip, AudioFileClip
from facenet_pytorch import MTCNN
from configs.inference_config import InferenceConfig

ffmpeg_path = os.getenv('FFMPEG_PATH')
if ffmpeg_path is None and platform.system() in ['Linux', 'Darwin']:
    try:
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
        if result.returncode == 0:
            ffmpeg_path = result.stdout.strip()
            print(f"FFmpeg is installed at: {ffmpeg_path}")
        else:
            print("FFmpeg is not installed. Please download ffmpeg-static and export to FFMPEG_PATH.")
            print("For example: export FFMPEG_PATH=/musetalk/ffmpeg-4.4-amd64-static")
    except Exception as e:
        pass

if ffmpeg_path is not None and ffmpeg_path not in os.getenv('PATH'):
    print("Adding FFMPEG_PATH to PATH")
    os.environ["PATH"] = f"{ffmpeg_path}:{os.environ['PATH']}"

def select_face(det_bboxes, probs):
    ## max face from faces that the prob is above 0.8
    ## box: xyxy
    if det_bboxes is None or probs is None:
        return None
    filtered_bboxes = []
    for bbox_i in range(len(det_bboxes)):
        if probs[bbox_i] > 0.8:
            filtered_bboxes.append(det_bboxes[bbox_i])
    if len(filtered_bboxes) == 0:
        return None

    sorted_bboxes = sorted(filtered_bboxes, key=lambda x:(x[3]-x[1]) * (x[2] - x[0]), reverse=True)
    return sorted_bboxes[0]


config: InferenceConfig = InferenceConfig()

############# model_init started #############

## vae init
vae = AutoencoderKL.from_pretrained(
    config.model_configs.pretrained_vae_path,
).to("cuda", dtype=config.weight_dtype)

## reference net init
reference_unet = UNet2DConditionModel.from_pretrained(
    config.model_configs.pretrained_base_model_path,
    subfolder="unet",
).to(dtype=config.weight_dtype, device=config.device)
reference_unet.load_state_dict(
    torch.load(config.model_configs.reference_unet_path, map_location="cpu"),
)

## denoising net init
if os.path.exists(config.model_configs.motion_module_path):
    ### stage1 + stage2
    denoising_unet = EchoUNet3DConditionModel.from_pretrained_2d(
        config.model_configs.pretrained_base_model_path,
        config.model_configs.motion_module_path,
        subfolder="unet",
        unet_additional_kwargs=config.infer_configs.unet_additional_kwargs,
    ).to(dtype=config.weight_dtype, device=config.device)
else:
    ### only stage1
    denoising_unet = EchoUNet3DConditionModel.from_pretrained_2d(
        config.model_configs.pretrained_base_model_path,
        "",
        subfolder="unet",
        unet_additional_kwargs={
            "use_motion_module": False,
            "unet_use_temporal_attention": False,
            "cross_attention_dim": config.infer_configs.unet_additional_kwargs.cross_attention_dim
        }
    ).to(dtype=config.weight_dtype, device=config.device)
denoising_unet.load_state_dict(
    torch.load(config.model_configs.denoising_unet_path, map_location="cpu"),
    strict=False
)

## face locator init
face_locator = FaceLocator(320, conditioning_channels=1, block_out_channels=(16, 32, 96, 256)).to(
    dtype=config.weight_dtype, device=config.device
)
face_locator.load_state_dict(torch.load(config.model_configs.face_locator_path))

### load audio processor params
audio_processor = load_audio_model(model_path=config.model_configs.audio_model_path, device=config.device)

### load face detector params
face_detector = MTCNN(image_size=320, margin=0, min_face_size=20, thresholds=[0.6, 0.7, 0.7], factor=0.709, post_process=True, device=device)

############# model_init finished #############

def generate_video(ref_image_path, audio_path, output_path):
    width, height = config.width, config.height
    sched_kwargs = OmegaConf.to_container(config.infer_configs.noise_scheduler_kwargs)
    scheduler = DDIMScheduler(**sched_kwargs)

    pipe = Audio2VideoPipeline(
        vae=vae,
        reference_unet=reference_unet,
        denoising_unet=denoising_unet,
        audio_guider=audio_processor,
        face_locator=face_locator,
        scheduler=scheduler,
    )
    pipe = pipe.to("cuda", dtype=config.weight_dtype)

    date_str = datetime.now().strftime("%Y%m%d")
    time_str = datetime.now().strftime("%H%M")
    save_dir_name = f"{time_str}--seed_{config.seed}-{config.width}x{config.height}"
    save_dir = Path(f"output/{date_str}/{save_dir_name}")
    save_dir.mkdir(exist_ok=True, parents=True)

    if config.seed is not None and config.seed > -1:
        generator = torch.manual_seed(config.seed)
    else:
        generator = torch.manual_seed(random.randint(100, 1000000))

    ref_name = Path(ref_image_path).stem
    audio_name = Path(audio_path).stem
    final_fps = config.fps

    #### face musk prepare
    face_img = cv2.imread(ref_image_path)
    face_mask = np.zeros((face_img.shape[0], face_img.shape[1])).astype('uint8')

    det_bboxes, probs = face_detector.detect(face_img)
    select_bbox = select_face(det_bboxes, probs)
    if select_bbox is None:
        face_mask[:, :] = 255
    else:
        xyxy = select_bbox[:4]
        xyxy = np.round(xyxy).astype('int')
        rb, re, cb, ce = xyxy[1], xyxy[3], xyxy[0], xyxy[2]
        r_pad = int((re - rb) * config.facemusk_dilation_ratio)
        c_pad = int((ce - cb) * config.facemusk_dilation_ratio)
        face_mask[rb - r_pad : re + r_pad, cb - c_pad : ce + c_pad] = 255

        #### face crop
        r_pad_crop = int((re - rb) * config.facecrop_dilation_ratio)
        c_pad_crop = int((ce - cb) * config.facecrop_dilation_ratio)
        crop_rect = [max(0, cb - c_pad_crop), max(0, rb - r_pad_crop), min(ce + c_pad_crop, face_img.shape[1]), min(re + r_pad_crop, face_img.shape[0])]
        print(crop_rect)
        face_img, _ = crop_and_pad(face_img, crop_rect)
        face_mask, _ = crop_and_pad(face_mask, crop_rect)
        face_img = cv2.resize(face_img, (config.width, config.height))
        face_mask = cv2.resize(face_mask, (config.width, config.height))

    ref_image_pil = Image.fromarray(face_img[:, :, [2, 1, 0]])
    face_mask_tensor = torch.Tensor(face_mask).to(dtype=config.weight_dtype, device="cuda").unsqueeze(0).unsqueeze(0).unsqueeze(0) / 255.0

    video = pipe(
        ref_image_pil,
        audio_path,
        face_mask_tensor,
        width,
        height,
        config.length,
        config.steps,
        config.cfg,
        generator=generator,
        audio_sample_rate=config.sample_rate,
        context_frames=config.context_frames,
        fps=final_fps,
        context_overlap=config.context_overlap
    ).videos

    video = video
    
    save_videos_grid(
        video,
        f"{save_dir}/{ref_name}_{audio_name}_{config.height}x{config.width}_{int(config.cfg)}_{time_str}.mp4",
        n_rows=1,
        fps=final_fps,
    )

    video_clip = VideoFileClip(f"{save_dir}/{ref_name}_{audio_name}_{args.H}x{args.W}_{int(args.cfg)}_{time_str}.mp4")
    audio_clip = AudioFileClip(audio_path)
    video_clip = video_clip.set_audio(audio_clip)
    video_clip.write_videofile(f"{save_dir}/{ref_name}_{audio_name}_{args.H}x{args.W}_{int(args.cfg)}_{time_str}_withaudio.mp4", codec="libx264", audio_codec="aac")
    print(f"{save_dir}/{ref_name}_{audio_name}_{args.H}x{args.W}_{int(args.cfg)}_{time_str}_withaudio.mp4")
    torch.cuda.empty_cache()


