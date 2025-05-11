import os
import uuid
import time
import shutil

from flask import Blueprint, request, send_file, jsonify, current_app
from werkzeug.utils import secure_filename
from typing import Tuple
from . import temp_file_bp
from .temp_file_manager import temp_file_manager

UPLOAD_TMP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../uploads/tmpfiles')
IMAGE_TMP_FOLDER = os.path.join(UPLOAD_TMP_FOLDER, 'images')
AUDIO_TMP_FOLDER = os.path.join(UPLOAD_TMP_FOLDER, 'audio')
VIDEO_TMP_FOLDER = os.path.join(UPLOAD_TMP_FOLDER, 'video')

os.makedirs(IMAGE_TMP_FOLDER, exist_ok=True)
os.makedirs(AUDIO_TMP_FOLDER, exist_ok=True)
os.makedirs(VIDEO_TMP_FOLDER, exist_ok=True)

# 允许的文件类型
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'aac', 'm4a', 'flac'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'mpeg', 'mpg', 'm4v', 'webm', 'mkv'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_AUDIO_EXTENSIONS).union(ALLOWED_VIDEO_EXTENSIONS)

def allowed_file(filename):
    """检查文件类型是否允许上传"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_audio_file(filename):
    """检查是否为音频文件"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def is_image_file(filename):
    """检查是否为图片文件"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def is_video_file(filename):
    """检查是否为视频文件"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def get_file_path_type(file_name: str) -> Tuple[str, str]:
    """
    获取文件路径和文件类型
    
    Args:
        file_name: 文件名
        
    Returns:
        file_path: 文件路径
        file_type: 文件类型
    """
    if allowed_file(file_name):
        filename = secure_filename(file_name)
        file_type = ''
        
        if is_image_file(filename):
            file_type = 'image'
            save_folder = IMAGE_TMP_FOLDER
        elif is_audio_file(filename):
            file_type = 'audio'
            save_folder = AUDIO_TMP_FOLDER
        elif is_video_file(filename):
            file_type = 'video'
            save_folder = VIDEO_TMP_FOLDER
        else:
            return jsonify({'success': False, 'message': '不支持的文件类型'}), 400
        
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(save_folder, unique_filename)
        return file_path, file_type



@temp_file_bp.route('/upload', methods=['POST'])
def upload_temp_file():
    """上传临时文件接口"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有文件上传'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_type = ''
        
        if is_image_file(filename):
            file_type = 'image'
            save_folder = IMAGE_TMP_FOLDER
        elif is_audio_file(filename):
            file_type = 'audio'
            save_folder = AUDIO_TMP_FOLDER
        elif is_video_file(filename):
            file_type = 'video'
            save_folder = VIDEO_TMP_FOLDER
        else:
            return jsonify({'success': False, 'message': '不支持的文件类型'}), 400
        
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(save_folder, unique_filename)
        
        file.save(file_path)
        
        # 添加到临时文件管理器
        file_id = temp_file_manager.add_file(file_path, filename, file_type)
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'file_type': file_type,
            'original_name': filename
        })
    
    return jsonify({'success': False, 'message': '不允许的文件类型'}), 400

@temp_file_bp.route('/download/<file_id>', methods=['GET'])
def download_temp_file(file_id):
    """下载临时文件接口"""
    file_info = temp_file_manager.get_file(file_id)
    
    if file_info is None:
        return jsonify({'success': False, 'message': '文件不存在或已过期'}), 404
    
    return send_file(
        file_info['path'],
        download_name=file_info['original_name'],
        as_attachment=True
    )

@temp_file_bp.route('/delete/<file_id>', methods=['DELETE'])
def delete_temp_file(file_id):
    """删除临时文件接口"""
    if temp_file_manager.delete_file(file_id):
        return jsonify({'success': True, 'message': '文件删除成功'})
    
    return jsonify({'success': False, 'message': '文件不存在或已过期'}), 404

@temp_file_bp.route('/batch-delete', methods=['POST'])
def batch_delete_files():
    """批量删除临时文件接口"""
    data = request.get_json()
    if not data or 'file_ids' not in data or not isinstance(data['file_ids'], list):
        return jsonify({'success': False, 'message': '请求格式错误'}), 400
    
    success_count = temp_file_manager.delete_files(data['file_ids'])
    
    return jsonify({
        'success': True,
        'message': f'成功删除{success_count}个文件',
        'deleted_count': success_count
    })

# 定期清理过期文件
def cleanup_task():
    """定期清理过期文件的任务"""
    return temp_file_manager.cleanup_expired()