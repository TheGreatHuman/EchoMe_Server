from typing import Dict, Any, List, Union, Optional
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.ai_role_model import AIRole
from app.models.user_model import User
from ..utils import convert_str_to_uuid_bytes

@jwt_required()
def get_role_detail() -> tuple[jsonify, int]:
    """获取AI角色详情接口"""
    try:
        # 获取当前用户ID
        current_user_id_bytes = convert_str_to_uuid_bytes(get_jwt_identity())

        # 解析请求参数
        data = request.get_json() or {}
        role_id = data.get('role_id')

        # 校验必填参数
        if not role_id:
            return jsonify({
                'code': 400,
                'message': 'Missing required field: role_id'
            }), 400

        # 转换role_id为bytes
        try:
            role_id_bytes = convert_str_to_uuid_bytes(role_id)
        except ValueError:
            return jsonify({
                'code': 400,
                'message': 'Invalid role_id format'
            }), 400

        # 查询角色详情
        role_data = db.session.query(
            AIRole,
            User.username.label('created_by_username')
        ).join(User, AIRole.created_by == User.id).filter(
            AIRole.role_id == role_id_bytes
        ).first()

        if not role_data:
            return jsonify({
                'code': 404,
                'message': 'Role not found'
            }), 404

        role, created_by_username = role_data

        # 检查权限
        if not role.is_public and role.created_by != current_user_id_bytes:
            return jsonify({
                'code': 403,
                'message': 'Permission denied'
            }), 403

        # 构建响应数据
        is_mine = (role.created_by == current_user_id_bytes)
        role_dict = role.to_dict()
        role_dict['created_by_username'] = created_by_username
        role_dict['is_created_by_current_user'] = is_mine

        return jsonify({
            'code': 200,
            'message': 'get role detail success',
            'role': role_dict
        }), 200

    except Exception as e:
        print(f"Error in get_role_detail: {e}")
        return jsonify({
            'code': 500,
            'message': 'get role detail fail',
            'error_info': str(e)
        }), 500

@jwt_required()
def get_created_roles() -> tuple[jsonify, int]:
    """获取当前用户创建的所有AI角色"""
    try:
        # 从JWT获取当前用户ID
        current_user_id_str = get_jwt_identity()
        current_user_id_bytes = convert_str_to_uuid_bytes(current_user_id_str)
        
        # 查询用户创建的所有角色信息
        roles_data = db.session.query(
            AIRole,
            User.username.label('created_by_username')
        ).join(
            User, AIRole.created_by == User.id
        ).filter(
            AIRole.created_by == current_user_id_bytes
        ).all()
        
        if not roles_data:
            return jsonify({
                'code': 200,
                'message': 'no roles found',
                'roles': []
            }), 200
        
        # 处理返回数据
        roles_list = []
        for role, created_by_username in roles_data:
            # voice_id_str = role.voice_id) if role.voice_id else None
            
            roles_list.append({
                'role_id': role.role_id_str,
                'name': role.name,
                'gender': role.gender,
                'age': role.age,
                'personality': role.personality,
                'avatar_url': role.avatar_url_str,
                'voice_name': role.voice_name,
                'voice_id': role.voice_id_str,
                'response_language': role.response_language,
                'image_urls': role.image_urls,
                'created_at': role.created_at.isoformat() + 'Z',
                'role_color': role.role_color,
                'created_by_username': created_by_username,
                'created_by_user_id': role.created_by_user_id_str,
                'is_public': role.is_public,
                'used_num': role.used_num,
                'is_created_by_current_user': True
            })
        
        return jsonify({
            'code': 200,
            'message': 'get created roles success',
            'roles': roles_list
        }), 200
    
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'Server error: {str(e)}'
        }), 500