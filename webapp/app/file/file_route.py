import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app import db
from . import file_bp
from app.models.file_model import File
from app.models.user_model import User
import re

# 配置上传文件存储路径
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../uploads/files')
IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')
AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, 'audio')
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)


# 允许的文件类型
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'aac', 'm4a', 'flac'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_AUDIO_EXTENSIONS)

def allowed_file(filename):
    """检查文件类型是否允许上传"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_audio_file(filename):
    """检查是否为音频文件"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def is_image_file(filename):
    """检查是否为图片文件"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@file_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """上传文件接口（支持图片和音频）"""
    try:
        current_user_id = get_jwt_identity()
        
        # 检查是否有文件部分
        if 'file' not in request.files:
            return jsonify({
                'code': 400,
                'message': 'upload file fail',
                'error_info': 'No file part'
            }), 400
            
        file = request.files['file']
        
        # 检查文件名是否为空
        if file.filename == '':
            return jsonify({
                'code': 400,
                'message': 'upload file fail',
                'error_info': 'No selected file'
            }), 400
            
        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({
                'code': 400,
                'message': 'upload file fail',
                'error_info': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
            
        # 获取是否为私有文件
        is_public = request.form.get('is_public', 'true').lower() == 'true'
        description = request.form.get('description', '')
        
        # 安全处理文件名并生成唯一文件名
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        
        # 根据文件类型选择保存路径
        if is_audio_file(filename):
            save_folder = AUDIO_FOLDER
        else:
            save_folder = IMAGE_FOLDER
            
        # 保存文件
        file_path = os.path.join(save_folder, unique_filename)
        file.save(file_path)
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        
        # 获取文件MIME类型
        file_type = file.content_type
        
        # 创建文件记录
        new_file = File(
            file_name=filename,
            file_path=unique_filename,  # 只存储相对路径
            file_size=file_size,
            file_type=file_type,
            created_by=current_user_id,
            is_public=is_public,
            description=description
        )
        
        db.session.add(new_file)
        db.session.commit()
        
        # 返回文件信息
        return jsonify({
            'code': 201,
            'message': 'upload file success',
            'file_id': new_file.file_id_str,
            'file_name': new_file.file_name,
            'file_path': f"/api/file/download/{new_file.file_id_str}",
            'file_size': new_file.file_size,
            'file_type': new_file.file_type,
            'is_private': new_file.is_public,
            'created_at': new_file.created_at.isoformat() + 'Z'
        }), 201
        
    except Exception as e:
        print(e)
        return jsonify({
            'code': 500,
            'message': 'upload file fail',
            'error_info': str(e)
        }), 500

@file_bp.route('/download/<file_id>', methods=['GET'])
@jwt_required()
def download_file(file_id):
    """下载文件接口（支持图片和音频）"""
    try:
        current_user_id = get_jwt_identity()
        
        # 查找文件记录
        file: File = File.query.filter(File.file_id == uuid.UUID(file_id).bytes).first()
        
        if not file:
            return jsonify({
                'code': 404,
                'message': 'download file fail',
                'error_info': 'File not found'
            }), 404
            
        # 检查权限
        if not file.is_public and file.created_by_user_id_str != current_user_id:
            return jsonify({
                'code': 403,
                'message': 'download file fail',
                'error_info': 'You do not have permission to access this file'
            }), 403
            
        # 判断文件类型并构建完整路径
        file_ext = file.file_path.rsplit('.', 1)[1].lower() if '.' in file.file_path else ''
        if file_ext in ALLOWED_AUDIO_EXTENSIONS:
            file_path = os.path.join(AUDIO_FOLDER, file.file_path)
        else:
            file_path = os.path.join(IMAGE_FOLDER, file.file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({
                'code': 404,
                'message': 'download file fail',
                'error_info': 'File not found on server'
            }), 404
            
        # 检查 Range 请求
        range_header = request.headers.get('Range', None)
        if not range_header:
            # 没有 Range，直接返回整个文件
            return send_file(file_path, mimetype=file.file_type, as_attachment=False, download_name=file.file_name)

        # 有 Range，解析
        size = os.path.getsize(file_path)
        byte1, byte2 = 0, None
        m = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if m:
            g = m.groups()
            byte1 = int(g[0])
            if g[1]:
                byte2 = int(g[1])
        length = size - byte1 if byte2 is None else byte2 - byte1 + 1

        with open(file_path, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)

        rv = Response(data,
                    206,
                    mimetype=file.file_type,
                    content_type=file.file_type,
                    direct_passthrough=True)
        rv.headers.add('Content-Range', f'bytes {byte1}-{byte1 + length - 1}/{size}')
        rv.headers.add('Accept-Ranges', 'bytes')
        rv.headers.add('Content-Length', str(length))
        return rv
        # 返回文件
        # return send_file(file_path, mimetype=file.file_type, as_attachment=False, download_name=file.file_name)
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'download file fail',
            'error_info': str(e)
        }), 500

@file_bp.route('/list', methods=['POST'])
@jwt_required()
def list_files():
    """获取文件列表接口"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        page = data.get('page', 1)
        page_size = data.get('page_size', 10)
        only_mine = data.get('only_mine', False)
        
        if not isinstance(page, int) or page < 1:
            page = 1
        if not isinstance(page_size, int) or page_size < 1:
            page_size = 10
            
        # 构建查询
        query = db.session.query(
            File.file_id,
            File.file_id_str,
            File.file_name,
            File.file_path,
            File.file_size,
            File.file_type,
            File.created_at,
            File.created_by,
            File.created_by_user_id_str,
            File.is_public,
            File.description,
            User.username.label('created_by_username')
        ).join(User, File.created_by == User.id)
        
        # 过滤条件
        if only_mine:
            # 只显示当前用户的文件
            query = query.filter(File.created_by_user_id_str == current_user_id)
        else:
            # 显示公开文件和当前用户的私有文件
            query = query.filter(
                (File.is_public == True) | 
                ((File.is_public == False) & (File.created_by_user_id_str == current_user_id))
            )
            
        # 计算总数
        total_items = query.count()
        total_pages = (total_items + page_size - 1) // page_size
        has_next = page < total_pages
        
        # 应用分页
        offset = (page - 1) * page_size
        files_data = query.order_by(File.created_at.desc()).limit(page_size).offset(offset).all()
        
        if not files_data:
            return jsonify({
                'code': 200,
                'message': 'no files found',
                'has_next': has_next,
                'files': []
            }), 200
            
        # 格式化结果
        files_list = []
        for file in files_data:
            is_owner = (file.created_by_user_id_str == current_user_id)
            files_list.append({
                'file_id': file.file_id_str,
                'file_name': file.file_name,
                'file_path': f"/api/file/download/{file.file_id_str}",
                'file_size': file.file_size,
                'file_type': file.file_type,
                'created_at': file.created_at.isoformat() + 'Z',
                'created_by_username': file.created_by_username,
                'created_by_user_id': file.created_by_user_id_str,
                'is_public': file.is_public,
                'description': file.description,
                'is_owner': is_owner
            })
            
        return jsonify({
            'code': 200,
            'message': 'get files success',
            'has_next': has_next,
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'files': files_list
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'get files fail',
            'error_info': str(e)
        }), 500

@file_bp.route('/delete/<file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(file_id):
    """删除文件接口"""
    try:
        current_user_id = get_jwt_identity()
        
        # 查找文件记录
        file = File.query.filter(File.file_id_str == file_id).first()
        
        if not file:
            return jsonify({
                'code': 404,
                'message': 'delete file fail',
                'error_info': 'File not found'
            }), 404
            
        # 检查权限（只有文件所有者可以删除）
        if file.created_by_user_id_str != current_user_id:
            return jsonify({
                'code': 403,
                'message': 'delete file fail',
                'error_info': 'You do not have permission to delete this file'
            }), 403
            
        # 判断文件类型并构建完整路径
        file_ext = file.file_path.rsplit('.', 1)[1].lower() if '.' in file.file_path else ''
        if file_ext in ALLOWED_AUDIO_EXTENSIONS:
            file_path = os.path.join(AUDIO_FOLDER, file.file_path)
        else:
            file_path = os.path.join(IMAGE_FOLDER, file.file_path)
        
        # 删除物理文件
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # 删除数据库记录
        db.session.delete(file)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': 'delete file success'
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'delete file fail',
            'error_info': str(e)
        }), 500

@file_bp.route('/update/<file_id>', methods=['PUT'])
@jwt_required()
def update_file(file_id):
    """更新文件信息接口"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'code': 400,
                'message': 'update file fail',
                'error_info': 'No data provided'
            }), 400
            
        # 查找文件记录
        file: File = File.query.filter(File.file_id_str == file_id).first()
        
        if not file:
            return jsonify({
                'code': 404,
                'message': 'update file fail',
                'error_info': 'File not found'
            }), 404
            
        # 检查权限（只有文件所有者可以更新）
        if file.created_by_user_id_str != current_user_id:
            return jsonify({
                'code': 403,
                'message': 'update file fail',
                'error_info': 'You do not have permission to update this file'
            }), 403
            
        # 更新文件信息
        if 'file_name' in data:
            file.file_name = data['file_name']
            
        if 'is_private' in data:
            file.is_public = data['is_public']
            
        if 'description' in data:
            file.description = data['description']
            
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': 'update file success',
            'file': file.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'update file fail',
            'error_info': str(e)
        }), 500

@file_bp.route('/update_content/<file_id>', methods=['POST'])
@jwt_required()
def update_file_content(file_id):
    """更新文件内容接口"""
    try:
        current_user_id = get_jwt_identity()
        
        # 检查是否有文件部分
        if 'file' not in request.files:
            return jsonify({
                'code': 400,
                'message': 'update file content fail',
                'error_info': 'No file part'
            }), 400
            
        file_upload = request.files['file']
        
        # 检查文件名是否为空
        if file_upload.filename == '':
            return jsonify({
                'code': 400,
                'message': 'update file content fail',
                'error_info': 'No selected file'
            }), 400
            
        # 检查文件类型
        if not allowed_file(file_upload.filename):
            return jsonify({
                'code': 400,
                'message': 'update file content fail',
                'error_info': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
            
        # 查找文件记录
        file: File = File.query.filter(File.file_id == uuid.UUID(file_id).bytes).first()
        
        if not file:
            return jsonify({
                'code': 404,
                'message': 'update file content fail',
                'error_info': 'File not found'
            }), 404
            
        # 检查权限（只有文件所有者可以更新）
        if file.created_by_user_id_str != current_user_id:
            return jsonify({
                'code': 403,
                'message': 'update file content fail',
                'error_info': 'You do not have permission to update this file'
            }), 403
            
        # 检查新文件类型是否与原文件类型兼容
        new_file_type = file_upload.content_type
        is_new_audio = is_audio_file(file_upload.filename)
        is_old_audio = file.file_type.startswith('audio/') or file.file_path.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS
        
        if (is_new_audio and not is_old_audio) or (not is_new_audio and is_old_audio):
            return jsonify({
                'code': 400,
                'message': 'update file content fail',
                'error_info': 'New file type does not match original file type category (audio/image)'
            }), 400
            
        # 获取原文件路径并删除
        file_ext = file.file_path.rsplit('.', 1)[1].lower() if '.' in file.file_path else ''
        if file_ext in ALLOWED_AUDIO_EXTENSIONS:
            old_file_path = os.path.join(AUDIO_FOLDER, file.file_path)
        else:
            old_file_path = os.path.join(IMAGE_FOLDER, file.file_path)
            
        if os.path.exists(old_file_path):
            os.remove(old_file_path)
            
        # 保存新文件（使用原文件名）
        if is_new_audio:
            save_folder = AUDIO_FOLDER
        else:
            save_folder = IMAGE_FOLDER
            
        file_path = os.path.join(save_folder, file.file_path)
        file_upload.save(file_path)
        
        # 更新文件记录
        file.file_size = os.path.getsize(file_path)
        file.file_type = new_file_type
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': 'update file content success',
            'file': file.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'update file content fail',
            'error_info': str(e)
        }), 500