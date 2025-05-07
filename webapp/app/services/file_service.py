#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from werkzeug.utils import secure_filename
from flask import current_app, send_file, request

logger = logging.getLogger(__name__)

class FileService:
    """
    聊天文件服务类，用于处理聊天过程中的临时文件上传和下载
    包括：用户上传的音频、AI生成的音频、AI生成的视频等
    """
    
    def __init__(self):
        """初始化文件服务"""
        # 获取配置的临时文件目录
        self.temp_dir = current_app.config.get('TEMP_FILE_DIR', 'temp')
        self.ensure_temp_dir()
        
        # 文件类型映射
        self.allowed_extensions = {
            'audio': {'wav', 'mp3', 'ogg', 'm4a'},
            'video': {'mp4', 'webm'},
            'image': {'jpg', 'jpeg', 'png', 'gif'}
        }
        
        # 文件过期时间（默认24小时）
        self.file_expiry = current_app.config.get('TEMP_FILE_EXPIRY', 24)
    
    def ensure_temp_dir(self) -> None:
        """确保临时文件目录存在"""
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            logger.info(f"创建临时文件目录: {self.temp_dir}")
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """
        生成唯一的文件名
        
        Args:
            original_filename: 原始文件名
            
        Returns:
            str: 生成的文件名
        """
        # 获取文件扩展名
        ext = os.path.splitext(original_filename)[1]
        # 生成UUID作为文件名
        return f"{uuid.uuid4().hex}{ext}"
    
    def _get_file_type(self, filename: str) -> Optional[str]:
        """
        根据文件扩展名判断文件类型
        
        Args:
            filename: 文件名
            
        Returns:
            Optional[str]: 文件类型（audio/video/image）或None
        """
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        for file_type, extensions in self.allowed_extensions.items():
            if ext in extensions:
                return file_type
        
        return None
    
    def save_uploaded_file(self, file, file_type: str = 'audio') -> Tuple[bool, str, Optional[str]]:
        """
        保存上传的文件
        
        Args:
            file: 上传的文件对象
            file_type: 文件类型（audio/video/image）
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 消息, 文件URL)
        """
        try:
            if not file:
                return False, "未提供文件", None
            
            filename = secure_filename(file.filename)
            if not filename:
                return False, "无效的文件名", None
            
            # 检查文件类型
            detected_type = self._get_file_type(filename)
            if not detected_type or detected_type != file_type:
                return False, f"不支持的文件类型，请上传{file_type}文件", None
            
            # 生成唯一文件名
            unique_filename = self._generate_unique_filename(filename)
            file_path = os.path.join(self.temp_dir, unique_filename)
            
            # 保存文件
            file.save(file_path)
            
            # 生成访问URL
            file_url = f"/api/chat/files/{unique_filename}"
            
            logger.info(f"文件已保存: {file_path}")
            return True, "文件上传成功", file_url
            
        except Exception as e:
            logger.exception(f"保存文件时出错: {str(e)}")
            return False, f"保存文件失败: {str(e)}", None
    
    def get_file(self, filename: str) -> Tuple[bool, str, Optional[str]]:
        """
        获取文件
        
        Args:
            filename: 文件名
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 消息, 文件路径)
        """
        try:
            file_path = os.path.join(self.temp_dir, filename)
            
            if not os.path.exists(file_path):
                return False, "文件不存在", None
            
            # 检查文件是否过期
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            if datetime.now() - file_time > timedelta(hours=self.file_expiry):
                os.remove(file_path)
                return False, "文件已过期", None
            
            return True, "文件获取成功", file_path
            
        except Exception as e:
            logger.exception(f"获取文件时出错: {str(e)}")
            return False, f"获取文件失败: {str(e)}", None
    
    def delete_file(self, filename: str) -> Tuple[bool, str]:
        """
        删除文件
        
        Args:
            filename: 文件名
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            file_path = os.path.join(self.temp_dir, filename)
            
            if not os.path.exists(file_path):
                return False, "文件不存在"
            
            os.remove(file_path)
            logger.info(f"文件已删除: {file_path}")
            return True, "文件删除成功"
            
        except Exception as e:
            logger.exception(f"删除文件时出错: {str(e)}")
            return False, f"删除文件失败: {str(e)}"
    
    def cleanup_expired_files(self) -> Tuple[int, int]:
        """
        清理过期文件
        
        Returns:
            Tuple[int, int]: (成功删除数, 失败删除数)
        """
        success_count = 0
        fail_count = 0
        
        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                
                # 检查文件是否过期
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if datetime.now() - file_time > timedelta(hours=self.file_expiry):
                    try:
                        os.remove(file_path)
                        success_count += 1
                    except Exception:
                        fail_count += 1
            
            logger.info(f"清理过期文件完成: 成功={success_count}, 失败={fail_count}")
            return success_count, fail_count
            
        except Exception as e:
            logger.exception(f"清理过期文件时出错: {str(e)}")
            return success_count, fail_count 