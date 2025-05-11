import uuid
import time
import os
from typing import List, Dict, Any

class TempFileManager:
    """临时文件管理类，负责文件的增加、获取、删除等操作"""
    def __init__(self):
        self.file_map: Dict[str, Dict[str, Any]] = {}  # 文件ID到路径的映射
        self.expiry = {}  # 文件ID到过期时间的映射
        self.expiry_time = 24 * 60 * 60  # 默认24小时后过期
    
    def add_file(self, file_path: str, original_filename: str, file_type: str):
        """添加文件并返回唯一ID"""
        file_id = str(uuid.uuid4())
        self.file_map[file_id] = {
            'path': file_path,
            'original_name': original_filename,
            'type': file_type
        }
        # 获取应用配置的过期时间（小时），如果不存在则使用默认值
        expiry_hours = os.getenv('TEMP_FILE_EXPIRY', 24)
        self.expiry[file_id] = time.time() + (expiry_hours * 60 * 60)
        return file_id
    
    def get_file(self, file_id: str):
        """根据ID获取文件信息"""
        if file_id in self.file_map and time.time() < self.expiry[file_id]:
            return self.file_map[file_id]
        return None
    
    def delete_file(self, file_id: str):
        """删除指定ID的文件"""
        if file_id in self.file_map:
            file_path = self.file_map[file_id]['path']
            if os.path.exists(file_path):
                os.remove(file_path)
            del self.file_map[file_id]
            del self.expiry[file_id]
            return True
        return False
    
    def delete_files(self, file_ids: List[str]):
        """删除多个文件"""
        success_count = 0
        for file_id in file_ids:
            if self.delete_file(file_id):
                success_count += 1
        return success_count
    
    def cleanup_expired(self):
        """清理过期文件"""
        current_time = time.time()
        expired_ids = [fid for fid in self.expiry if current_time > self.expiry[fid]]
        return self.delete_files(expired_ids)
    
# 创建临时文件管理器实例
temp_file_manager = TempFileManager()