#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

from app.services.file_service import FileService

logger = logging.getLogger(__name__)

# 创建蓝图
chat_file_bp = Blueprint('chat_file', __name__, url_prefix='/api/chat/files')

# 创建文件服务实例
file_service = FileService()

@chat_file_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    上传聊天文件
    支持：用户音频、AI生成的音频/视频等
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '未提供文件'
            }), 400
        
        file = request.files['file']
        file_type = request.form.get('file_type', 'audio')
        
        # 保存文件
        success, message, file_url = file_service.save_uploaded_file(file, file_type)
        
        if not success:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'file_url': file_url
        })
        
    except Exception as e:
        logger.exception(f"上传文件时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'上传文件失败: {str(e)}'
        }), 500

@chat_file_bp.route('/<filename>', methods=['GET'])
def get_file(filename):
    """
    获取聊天文件
    """
    try:
        # 安全检查
        filename = secure_filename(filename)
        
        # 获取文件
        success, message, file_path = file_service.get_file(filename)
        
        if not success:
            return jsonify({
                'success': False,
                'message': message
            }), 404
        
        # 发送文件
        return send_file(file_path)
        
    except Exception as e:
        logger.exception(f"获取文件时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取文件失败: {str(e)}'
        }), 500

@chat_file_bp.route('/<filename>', methods=['DELETE'])
def delete_file(filename):
    """
    删除聊天文件
    """
    try:
        # 安全检查
        filename = secure_filename(filename)
        
        # 删除文件
        success, message = file_service.delete_file(filename)
        
        if not success:
            return jsonify({
                'success': False,
                'message': message
            }), 404
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        logger.exception(f"删除文件时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除文件失败: {str(e)}'
        }), 500

@chat_file_bp.route('/cleanup', methods=['POST'])
def cleanup_files():
    """
    清理过期文件
    """
    try:
        # 清理过期文件
        success_count, fail_count = file_service.cleanup_expired_files()
        
        return jsonify({
            'success': True,
            'message': f'清理完成: 成功={success_count}, 失败={fail_count}'
        })
        
    except Exception as e:
        logger.exception(f"清理文件时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'清理文件失败: {str(e)}'
        }), 500 