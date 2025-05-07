from typing import Dict, Any, List, Union, Optional
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.ai_role_model import AIRole
from app.models.user_role_relation_model import UserRoleRelation
from ..utils import (
    convert_str_to_uuid_bytes,
    validate_gender,
    validate_response_language
)

@jwt_required()
def create_role() -> tuple[jsonify, int]:
    """创建AI角色接口"""
    try:
        current_user_id_str = get_jwt_identity()

        # 解析请求参数
        data = request.get_json() or {}
        name = data.get('name')
        gender = data.get('gender')
        age = data.get('age')
        personality = data.get('personality')
        avatar_url = data.get('avatar_url')
        voice_name = data.get('voice_name')
        voice_id = data.get('voice_id')
        response_language = data.get('response_language')
        image_urls = data.get('image_urls')
        role_color = data.get('role_color')
        is_public = data.get('is_public', False)

        # 校验必填字段
        missing = [f for f in ('name', 'gender', 'personality', 'avatar_url', 'response_language')
                   if not data.get(f)]
        if missing:
            return jsonify({
                'code': 400,
                'message': f"Missing fields: {', '.join(missing)}"
            }), 400

        # 校验枚举值
        if not validate_gender(gender):
            return jsonify({
                'code': 400,
                'message': "gender must be one of 'male', 'female', or 'other'"
            }), 400

        if not validate_response_language(response_language):
            return jsonify({
                'code': 400,
                'message': "response_language must be one of 'chinese' or 'english'"
            }), 400

        # 创建角色实例
        role = AIRole(
            name=name,
            gender=gender,
            age=age,
            personality=personality,
            avatar_url=avatar_url,
            voice_name=voice_name,
            voice_id=voice_id,
            response_language=response_language,
            image_urls=image_urls,
            role_color=role_color,
            created_by=current_user_id_str,
            is_public=bool(is_public)
        )

        

        try:
            db.session.add(role)
            db.session.flush()
            # 创建用户角色关联
            user_role_relation = UserRoleRelation(
                user_id=current_user_id_str,
                role_id=role.role_id_str
            )
            db.session.add(user_role_relation)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

        return jsonify({
            'code': 200,
            'message': 'create role success',
            'role': role.to_dict()
        }), 200

    except Exception as e:
        print(f"Error in create_role: {e}")
        return jsonify({
            'code': 500,
            'message': 'create role fail',
            'error_info': str(e)
        }), 500

@jwt_required()
def update_role() -> tuple[jsonify, int]:
    """更新AI角色接口"""
    try:
        current_user_id_bytes = convert_str_to_uuid_bytes(get_jwt_identity())

        # 解析请求参数
        data = request.get_json() or {}
        role_id = data.get('role_id')

        if not role_id:
            return jsonify({
                'code': 400,
                'message': 'Missing required field: role_id'
            }), 400

        try:
            role_id_bytes = convert_str_to_uuid_bytes(role_id)
        except ValueError:
            return jsonify({
                'code': 400,
                'message': 'Invalid role_id format'
            }), 400

        # 查询角色
        role = db.session.query(AIRole).filter(AIRole.role_id == role_id_bytes).first()
        if not role:
            return jsonify({
                'code': 404,
                'message': 'Role not found'
            }), 404

        # 检查权限
        if role.created_by != current_user_id_bytes:
            return jsonify({
                'code': 403,
                'message': 'Permission denied: only creator can update role'
            }), 403

        # 可更新字段
        optional_fields = [
            'name', 'gender', 'age', 'personality', 'avatar_url',
            'voice_name', 'voice_id', 'response_language', 'image_urls',
            'role_color', 'is_public'
        ]

        # 更新字段
        for field in optional_fields:
            if field in data and data[field] is not None:
                if field in ['avatar_url', 'voice_id']:
                    try:
                        if data[field]:
                            setattr(role, field, convert_str_to_uuid_bytes(data[field]))
                        elif field == 'voice_id':
                            setattr(role, field, None)
                    except ValueError:
                        return jsonify({
                            'code': 400,
                            'message': f'Invalid {field} format'
                        }), 400
                elif field == 'image_urls':
                    if not isinstance(data[field], list):
                        return jsonify({
                            'code': 400,
                            'message': 'image_urls must be a list'
                        }), 400
                    role.image_urls = data[field]
                elif field == 'gender':
                    if not validate_gender(data[field]):
                        return jsonify({
                            'code': 400,
                            'message': "gender must be one of 'male', 'female', or 'other'"
                        }), 400
                    role.gender = data[field]
                elif field == 'response_language':
                    if not validate_response_language(data[field]):
                        return jsonify({
                            'code': 400,
                            'message': "response_language must be one of 'chinese' or 'english'"
                        }), 400
                    role.response_language = data[field]
                elif field == 'is_public':
                    role.is_public = bool(data[field])
                else:
                    setattr(role, field, data[field])

        db.session.commit()

        return jsonify({
            'code': 200,
            'message': 'update role success',
            'role': role.to_dict()
        }), 200

    except Exception as e:
        print(f"Error in update_role: {e}")
        return jsonify({
            'code': 500,
            'message': 'update role fail',
            'error_info': str(e)
        }), 500

@jwt_required()
def delete_role() -> tuple[jsonify, int]:
    """删除AI角色接口"""
    try:
        current_user_id_bytes = convert_str_to_uuid_bytes(get_jwt_identity())

        # 解析请求参数
        data = request.get_json() or {}
        role_id = data.get('role_id')

        if not role_id:
            return jsonify({
                'code': 400,
                'message': 'Missing required field: role_id'
            }), 400

        try:
            role_id_bytes = convert_str_to_uuid_bytes(role_id)
        except ValueError:
            return jsonify({
                'code': 400,
                'message': 'Invalid role_id format'
            }), 400

        # 查询角色
        role = db.session.query(AIRole).filter(AIRole.role_id == role_id_bytes).first()
        if not role:
            return jsonify({
                'code': 404,
                'message': 'Role not found'
            }), 404

        # 检查权限
        if role.created_by != current_user_id_bytes:
            return jsonify({
                'code': 403,
                'message': 'Permission denied: only creator can delete role'
            }), 403

        # 删除角色
        db.session.delete(role)
        db.session.commit()

        return jsonify({
            'code': 200,
            'message': 'delete role success'
        }), 200

    except Exception as e:
        print(f"Error in delete_role: {e}")
        return jsonify({
            'code': 500,
            'message': 'delete role fail',
            'error_info': str(e)
        }), 500