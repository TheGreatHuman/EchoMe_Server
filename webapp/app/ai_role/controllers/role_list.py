from typing import Dict, Any, List, Union, Optional
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import math
from app import db
from app.models.ai_role_model import AIRole
from app.models.user_model import User
from app.models.user_role_relation_model import UserRoleRelation
from ..utils import (
    convert_uuid_to_str,
    convert_str_to_uuid_bytes,
    parse_image_urls,
    validate_pagination_params
)

@jwt_required()
def get_roles() -> tuple[jsonify, int]:
    """获取AI角色列表接口"""
    try:
        # 从 JWT 获取用户ID
        current_user_id_bytes = convert_str_to_uuid_bytes(get_jwt_identity())

        # 解析请求参数
        data = request.get_json() or {}
        key_word = data.get('key_word')
        page, page_size = validate_pagination_params(
            data.get('page', 1),
            data.get('page_size', 10)
        )
        gender = data.get('gender', 'all')
        created_by_current_user = data.get('created_by_current_user', False)

        # 构建基础查询
        query = db.session.query(
            AIRole.role_id,
            AIRole.name,
            AIRole.gender,
            AIRole.age,
            AIRole.personality,
            AIRole.avatar_url,
            AIRole.voice_name,
            AIRole.voice_id,
            AIRole.response_language,
            AIRole.image_urls,
            AIRole.created_at,
            AIRole.role_color,
            User.username.label('created_by_username'),
            AIRole.created_by,
            AIRole.is_public,
            AIRole.used_num,
            UserRoleRelation.id.label('relation_id')
        ).join(User, AIRole.created_by == User.id)\
        .outerjoin(UserRoleRelation, db.and_(
            UserRoleRelation.role_id == AIRole.role_id,
            UserRoleRelation.user_id == current_user_id_bytes
        ))

        # 应用过滤条件
        if created_by_current_user:
            query = query.filter(AIRole.created_by == current_user_id_bytes)
        else:
            query = query.filter(AIRole.is_public.is_(True))

        if gender != 'all':
            query = query.filter(AIRole.gender == gender)

        if key_word:
            query = query.filter(AIRole.name.like(f'%{key_word}%'))

        # 计算分页信息
        total_items = query.count()
        total_pages = math.ceil(total_items / page_size)
        has_next = page < total_pages

        # 获取分页数据
        roles_data = query.order_by(AIRole.role_id.asc())\
            .limit(page_size)\
            .offset((page - 1) * page_size)\
            .all()

        if not roles_data:
            return jsonify({
                'code': 200,
                'message': 'no role found',
                'has_next': has_next,
                'roles': []
            }), 200

        # 处理返回数据
        roles_list = []
        for role in roles_data:
            is_mine = (role.created_by == current_user_id_bytes)
            voice_id_str = convert_uuid_to_str(role.voice_id) if role.voice_id else None
            
            has_relation = role.relation_id is not None
            relation_id_str = convert_uuid_to_str(role.relation_id) if role.relation_id else None
            
            roles_list.append({
                'role_id': convert_uuid_to_str(role.role_id),
                'name': role.name,
                'gender': role.gender,
                'age': role.age,
                'personality': role.personality,
                'avatar_url': convert_uuid_to_str(role.avatar_url),
                'voice_name': role.voice_name,
                'voice_id': voice_id_str,
                'response_language': role.response_language,
                'image_urls': parse_image_urls(role.image_urls),
                'created_at': role.created_at.isoformat() + 'Z',
                'role_color': role.role_color,
                'created_by_username': role.created_by_username,
                'created_by_user_id': convert_uuid_to_str(role.created_by),
                'is_public': role.is_public,
                'used_num': role.used_num,
                'is_created_by_current_user': is_mine,
                'has_relation': has_relation,
                'relation_id': relation_id_str
            })

        return jsonify({
            'code': 200,
            'message': 'get roles success',
            'has_next': has_next,
            'roles': roles_list
        }), 200

    except Exception as e:
        print(f"Error in get_roles: {e}")
        return jsonify({
            'code': 500,
            'message': 'get roles fail',
            'error_info': str(e)
        }), 500