from typing import Dict, Any, List, Union, Optional
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.ai_role_model import AIRole
from app.models.user_role_relation_model import UserRoleRelation
from app.models.user_model import User
from ..utils import (
    convert_str_to_uuid_bytes,
    convert_uuid_to_str,
    parse_image_urls
)

@jwt_required()
def get_user_roles() -> tuple[jsonify, int]:
    """获取当前用户的所有AI角色关系及角色信息"""
    try:
        # 从JWT获取当前用户ID
        current_user_id_str = get_jwt_identity()
        current_user_id_bytes = convert_str_to_uuid_bytes(current_user_id_str)
        
        # 查询用户的所有角色关系及角色信息
        roles_data = db.session.query(
            AIRole,
            User.username.label('created_by_username'),
            UserRoleRelation.id.label('relation_id')
        ).join(
            UserRoleRelation, UserRoleRelation.role_id == AIRole.role_id
        ).join(
            User, AIRole.created_by == User.id
        ).filter(
            UserRoleRelation.user_id == current_user_id_bytes
        ).all()
        
        if not roles_data:
            return jsonify({
                'code': 200,
                'message': 'no roles found',
                'roles': []
            }), 200
        
        # 处理返回数据
        roles_list = []
        for role, created_by_username, relation_id in roles_data:
            is_mine = (role.created_by == current_user_id_bytes)
            voice_id_str = convert_uuid_to_str(role.voice_id) if role.voice_id else None
            
            roles_list.append({
                'role_id': role.role_id_str,
                'name': role.name,
                'gender': role.gender,
                'age': role.age,
                'personality': role.personality,
                'avatar_url': role.avatar_url_str,
                'voice_name': role.voice_name,
                'voice_id': voice_id_str,
                'response_language': role.response_language,
                'image_urls': parse_image_urls(role.image_urls),
                'created_at': role.created_at.isoformat() + 'Z',
                'role_color': role.role_color,
                'created_by_username': created_by_username,
                'created_by_user_id': role.created_by_user_id_str,
                'is_public': role.is_public,
                'used_num': role.used_num,
                'is_created_by_current_user': is_mine,
                'relation_id': convert_uuid_to_str(relation_id)
            })
        
        return jsonify({
            'code': 200,
            'message': 'get user roles success',
            'roles': roles_list
        }), 200
    
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'Server error: {str(e)}'
        }), 500

@jwt_required()
def add_user_role_relation() -> tuple[jsonify, int]:
    """为当前用户添加AI角色关系"""
    try:
        # 从JWT获取当前用户ID
        current_user_id_str = get_jwt_identity()
        
        # 解析请求参数
        data = request.get_json() or {}
        role_id = data.get('role_id')
        
        # 校验必填参数
        if not role_id:
            return jsonify({
                'code': 400,
                'message': 'Missing required field: role_id'
            }), 400
        
        # 检查角色是否存在
        try:
            role_id_bytes = convert_str_to_uuid_bytes(role_id)
            role = AIRole.query.filter_by(role_id=role_id_bytes).first()
            if not role:
                return jsonify({
                    'code': 404,
                    'message': 'Role not found'
                }), 404
        except ValueError:
            return jsonify({
                'code': 400,
                'message': 'Invalid role_id format'
            }), 400
        
        # 检查关系是否已存在
        existing_relation = UserRoleRelation.query.filter_by(
            user_id=convert_str_to_uuid_bytes(current_user_id_str),
            role_id=role_id_bytes
        ).first()
        
        if existing_relation:
            return jsonify({
                'code': 400,
                'message': 'Relation already exists'
            }), 400
        
        # 创建新的用户角色关系
        new_relation = UserRoleRelation(current_user_id_str, role_id)
        db.session.add(new_relation)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': 'add user role relation success',
            'relation': new_relation.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'Server error: {str(e)}'
        }), 500

@jwt_required()
def delete_user_role_relation() -> tuple[jsonify, int]:
    """删除用户角色关系"""
    try:
        # 从JWT获取当前用户ID
        current_user_id_str = get_jwt_identity()
        current_user_id_bytes = convert_str_to_uuid_bytes(current_user_id_str)
        
        # 解析请求参数
        data = request.get_json() or {}
        relation_id = data.get('relation_id')
        role_id = data.get('role_id')
        
        # 至少需要提供一个ID
        if not relation_id and not role_id:
            return jsonify({
                'code': 400,
                'message': 'Missing required field: relation_id or role_id'
            }), 400
        
        # 根据提供的ID查询关系
        query = UserRoleRelation.query.filter_by(user_id=current_user_id_bytes)
        
        if relation_id:
            try:
                relation_id_bytes = convert_str_to_uuid_bytes(relation_id)
                query = query.filter_by(id=relation_id_bytes)
            except ValueError:
                return jsonify({
                    'code': 400,
                    'message': 'Invalid relation_id format'
                }), 400
        
        if role_id:
            try:
                role_id_bytes = convert_str_to_uuid_bytes(role_id)
                query = query.filter_by(role_id=role_id_bytes)
            except ValueError:
                return jsonify({
                    'code': 400,
                    'message': 'Invalid role_id format'
                }), 400
        
        # 查找并删除关系
        relation = query.first()
        if not relation:
            return jsonify({
                'code': 404,
                'message': 'Relation not found'
            }), 404
        
        relation_dict = relation.to_dict()  # 保存关系信息用于返回
        db.session.delete(relation)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': 'delete user role relation success',
            'relation': relation_dict
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'Server error: {str(e)}'
        }), 500