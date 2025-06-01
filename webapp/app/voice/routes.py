from typing import Dict, Any, List, Union
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import UUID
import uuid
import os
import tempfile
import requests
from app import db
from app.voice import voice_bp
from app.models.user_model import User
from app.models.voice_model import Voice
from app.models.file_model import File
import math

# 导入dashscope相关模块
import dashscope
from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer

# 设置dashscope API key
dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')

@voice_bp.route('/get_voices', methods=['POST'])
@jwt_required()
def get_voices() -> tuple[jsonify, int]:
    """获取音色列表接口"""
    try:
        # 从 JWT 拿到的是 UUID 字符串，在 Python 层转成 bytes
        current_user_id_str = get_jwt_identity()
        current_user_id_bytes = UUID(current_user_id_str).bytes

        data = request.get_json() or {}
        key_word = data.get('key_word')
        page = data.get('page', 1)
        page_size = data.get('page_size', 10)
        gender = data.get('gender', 'all')
        created_by_current_user = data.get('created_by_current_user', False)

        # 校验分页参数
        if not isinstance(page, int) or page < 1:
            page = 1
        if not isinstance(page_size, int) or page_size < 1:
            page_size = 10

        # 基本查询：只拿二进制列，字符串转换留给 Python
        query = db.session.query(
            Voice.voice_id,
            Voice.voice_name,
            Voice.voice_gender,
            Voice.voice_url,
            User.username.label('created_by_username'),
            Voice.created_by,
            Voice.voice_description,
            Voice.created_at,
            Voice.is_public
        ).join(User, Voice.created_by == User.id)

        # 过滤：如果只看自己的
        if created_by_current_user:
            query = query.filter(Voice.created_by == current_user_id_bytes)
        else:
            query = query.filter(Voice.is_public.is_(True))

        # 按性别过滤
        if gender != 'all':
            query = query.filter(Voice.voice_gender == gender)

        # 按关键字
        if key_word:
            query = query.filter(Voice.voice_name.like(f'%{key_word}%'))

        # 统计总数 & 计算是否有下一页
        total_items = query.count()
        total_pages = math.ceil(total_items / page_size)
        has_next = page < total_pages

        # 分页 & 排序
        offset = (page - 1) * page_size
        voices_data = (
            query
            .order_by(Voice.voice_id.asc())
            .limit(page_size)
            .offset(offset)
            .all()
        )

        if not voices_data:
            return jsonify({
                'code': 200,
                'message': 'no voice found',
                'has_next': has_next,
                'voices': None
            }), 200

        # 把二进制 UUID 在 Python 层转为字符串
        voices_list = []
        for voice in voices_data:
            is_mine = (voice.created_by == current_user_id_bytes)
            voices_list.append({
                'voice_id': str(UUID(bytes=voice.voice_id)),
                'voice_name': voice.voice_name,
                'voice_gender': voice.voice_gender,
                'voice_audition_url': str(UUID(bytes=voice.voice_url)),
                'created_by_username': voice.created_by_username,
                'created_by_user_id': str(UUID(bytes=voice.created_by)),
                'voice_description': voice.voice_description,
                'created_at': voice.created_at.isoformat() + 'Z',
                'is_public': voice.is_public,
                'is_created_by_current_user': is_mine
            })

        return jsonify({
            'code': 200,
            'message': 'get voice success',
            'has_next': has_next,
            'voices': voices_list
        }), 200

    except Exception as e:
        # 实际项目里请用日志框架
        # print(f"Error in get_voices: {e}")
        return jsonify({
            'code': 500,
            'message': 'get voice fail',
            'error_info': str(e)
        }), 500


@voice_bp.route('/create_voice', methods=['POST'])
@jwt_required()
def create_voice() -> tuple[jsonify, int]:
    """创建新的音色接口"""
    try:
        # 1. 从 JWT 拿 UUID 字符串
        current_user_id_str = get_jwt_identity()

        # 2. 解析请求体
        data = request.get_json() or {}
        audio_file_id     = data.get('audio_file_id')  # 音频文件ID
        voice_name        = data.get('voice_name')
        voice_gender      = data.get('voice_gender')
        voice_description = data.get('voice_description')
        is_public         = data.get('is_public', False)

        # 3. 校验必填字段
        missing = [f for f in ('audio_file_id', 'voice_name', 'voice_gender', 'voice_description')
                   if not data.get(f)]
        if missing:
            return jsonify({
                'code': 400,
                'message': f"Missing fields: {', '.join(missing)}"
            }), 400

        # 4. 校验 voice_gender 值
        if voice_gender not in ('male','female','other'):
            return jsonify({
                'code': 400,
                'message': "voice_gender must be one of 'male', 'female', or 'other'"
            }), 400

        # 5. 强制 is_public 为布尔
        is_public = bool(is_public)


        # 7. 构建音频文件的下载URL
        base_url = "http://14.103.180.207:5000"
        audio_url = f"{base_url}/api/tempfile/download/{audio_file_id}"

        # 8. 调用dashscope创建音色
        try:
            target_model = "cosyvoice-v1"
            prefix = "digital"  # 使用用户ID前8位作为前缀
            
            # 创建语音注册服务实例
            service = VoiceEnrollmentService()
            
            # 调用create_voice方法复刻声音，并生成voice_id
            call_name = service.create_voice(target_model=target_model, prefix=prefix, url=audio_url)
            
            if not call_name:
                return jsonify({
                    'code': 500,
                    'message': 'Failed to create voice with dashscope'
                }), 500

        except Exception as e:
            return jsonify({
                'code': 500,
                'message': 'Dashscope API error',
                'error_info': str(e)
            }), 500

        # 9. 使用复刻的声音生成试听音频
        try:
            synthesizer = SpeechSynthesizer(model=target_model, voice=call_name)
            audio_data = synthesizer.call("今天天气怎么样？")
            
            if not audio_data:
                return jsonify({
                    'code': 500,
                    'message': 'Failed to generate audition audio'
                }), 500

        except Exception as e:
            return jsonify({
                'code': 500,
                'message': 'Audio synthesis error',
                'error_info': str(e)
            }), 500

        # 10. 将试听音频保存为临时文件并上传
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            # 准备上传到文件API
            upload_url = f"{base_url}/api/file/upload"
            
            # 获取用户请求时携带的JWT token
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('audition.mp3', f, 'audio/mpeg')}
                form_data = {
                    'is_public': 'false',  # 试听音频设为私有
                    'description': f'Voice audition for {voice_name}'
                }
                headers = {'Authorization': f'Bearer {token}'}
                
                response = requests.post(upload_url, files=files, data=form_data, headers=headers)
                
            # 清理临时文件
            os.unlink(temp_file_path)
            
            if response.status_code != 201:
                return jsonify({
                    'code': 500,
                    'message': 'Failed to upload audition audio',
                    'error_info': response.text
                }), 500
                
            upload_result = response.json()
            audition_file_id = upload_result.get('file_id')
            
            if not audition_file_id:
                return jsonify({
                    'code': 500,
                    'message': 'Failed to get audition file ID'
                }), 500

        except Exception as e:
            return jsonify({
                'code': 500,
                'message': 'File upload error',
                'error_info': str(e)
            }), 500

        # 11. 创建 Voice 实例
        voice = Voice(
            voice_name=voice_name,
            voice_url=audition_file_id,  # 使用试听音频的文件ID
            created_by=current_user_id_str,
            call_name=call_name,  # 使用dashscope返回的voice_id
            voice_gender=voice_gender,
            voice_description=voice_description,
            is_public=is_public
        )

        # 12. 持久化
        db.session.add(voice)
        db.session.commit()

        # 13. 返回新建结果
        return jsonify({
            'code': 200,
            'message': 'create voice success',
            'voice': voice.to_dict(),
            'dashscope_voice_id': call_name
        }), 200

    except Exception as e:
        # 注意：线上请用 logging
        # print(f"Error in create_voice: {e}")
        return jsonify({
            'code': 500,
            'message': 'create voice fail',
            'error_info': str(e)
        }), 500


@voice_bp.route('/my_voices', methods=['GET'])
@jwt_required()
def get_my_voices() -> tuple[jsonify, int]:
    """获取当前用户创建的音色列表接口"""
    try:
        # 从 JWT 拿到的是 UUID 字符串，在 Python 层转成 bytes
        current_user_id_str = get_jwt_identity()
        current_user_id_bytes = UUID(current_user_id_str).bytes
        
        # 基本查询：只拿二进制列，字符串转换留给 Python
        query = db.session.query(
            Voice.voice_id,
            Voice.voice_name,
            Voice.voice_gender,
            Voice.voice_url,
            User.username.label('created_by_username'),
            Voice.created_by,
            Voice.voice_description,
            Voice.created_at,
            Voice.is_public
        ).join(User, Voice.created_by == User.id)
        
        # 只查询当前用户创建的音色
        query = query.filter(Voice.created_by == current_user_id_bytes)
        
        # 获取所有结果
        voices_data = query.order_by(Voice.created_at.desc()).all()
        
        if not voices_data:
            return jsonify({
                'code': 200,
                'message': 'no voice found',
                'voices': []
            }), 200
        
        # 把二进制 UUID 在 Python 层转为字符串
        voices_list = []
        for voice in voices_data:
            voices_list.append({
                'voice_id': str(UUID(bytes=voice.voice_id)),
                'voice_name': voice.voice_name,
                'voice_gender': voice.voice_gender,
                'voice_audition_url': str(UUID(bytes=voice.voice_url)),
                'created_by_username': voice.created_by_username,
                'created_by_user_id': str(UUID(bytes=voice.created_by)),
                'voice_description': voice.voice_description,
                'created_at': voice.created_at.isoformat() + 'Z',
                'is_public': voice.is_public,
                'is_created_by_current_user': True
            })
        
        return jsonify({
            'code': 200,
            'message': 'get my voices success',
            'voices': voices_list
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'get my voices fail',
            'error_info': str(e)
        }), 500


@voice_bp.route('/verify_voice', methods=['POST'])
@jwt_required()
def verify_voice() -> tuple[jsonify, int]:
    """验证音频是否可获取并返回详细信息接口"""
    try:
        # 1. 从 JWT 拿到的是 UUID 字符串，在 Python 层转成 bytes
        current_user_id_str = get_jwt_identity()
        current_user_id_bytes = UUID(current_user_id_str).bytes

        # 2. 解析请求体
        data = request.get_json() or {}
        voice_id = data.get('voice_id')

        # 3. 校验必填字段
        if not voice_id:
            return jsonify({
                'code': 400,
                'message': 'Missing required field: voice_id'
            }), 400

        # 4. 将 voice_id 字符串转为 bytes
        try:
            voice_id_bytes = UUID(voice_id).bytes
        except ValueError:
            return jsonify({
                'code': 400,
                'message': 'Invalid voice_id format'
            }), 400

        # 5. 查询音频是否存在
        voice_data = db.session.query(
            Voice,
            User.username.label('created_by_username')
        ).join(User, Voice.created_by == User.id).filter(
            Voice.voice_id == voice_id_bytes
        ).first()

        if not voice_data:
            return jsonify({
                'code': 404,
                'message': 'Voice not found'
            }), 404

        voice, created_by_username = voice_data

        # 6. 检查权限：非公开音频只有创建者可以获取
        if not voice.is_public and voice.created_by != current_user_id_bytes:
            return jsonify({
                'code': 403,
                'message': 'Permission denied: voice is not public and you are not the creator'
            }), 403

        # 7. 构建响应数据
        is_mine = (voice.created_by == current_user_id_bytes)
        voice_dict = voice.to_dict()
        voice_dict['created_by_username'] = created_by_username
        voice_dict['is_created_by_current_user'] = is_mine

        return jsonify({
            'code': 200,
            'message': 'voice verification success',
            'voice': voice_dict,
            'can_access': True
        }), 200

    except Exception as e:
        # print(f"Error in verify_voice: {e}")
        return jsonify({
            'code': 500,
            'message': 'voice verification fail',
            'error_info': str(e)
        }), 500
