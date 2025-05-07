from flask import Blueprint, request, jsonify
from app.models.user_model import User
from app import db, jwt
from app.auth import auth_bp
from app.auth.utils import CaptchaManager, validate_identifier
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
import json


@auth_bp.route('/send_captcha', methods=['POST'])
def send_captcha():
    """发送验证码接口"""
    try:
        data = request.get_json()
        
        # 验证请求参数
        if not data or 'identifier' not in data or 'type' not in data:
            return jsonify({
                'code': 400,
                'message': 'send login code fail',
                'error_info': 'Missing required parameters'
            }), 400
        
        identifier = data['identifier']
        type_ = data['type']
        
        # 验证标识符格式
        is_valid, error_msg = validate_identifier(identifier, type_)
        if not is_valid:
            return jsonify({
                'code': 400,
                'message': 'send login code fail',
                'error_info': error_msg
            }), 400
        
        # 检查是否首次使用
        is_first_use = CaptchaManager.is_first_use(identifier, type_)
        
        # 生成验证码（在实际应用中，这里应该调用短信或邮件服务发送验证码）
        code = CaptchaManager.generate_captcha(identifier, type_)
        
        # 在开发环境中，可以直接返回验证码，方便测试
        if is_first_use:
            return jsonify({
                'code': 200,
                'message': f"{type_} first use",
                'is_first_use': True,
                'captcha': code  # 仅在开发环境返回
            }), 200
        else:
            return jsonify({
                'code': 204,
                'captcha': code  # 仅在开发环境返回
            }), 200
            
    except Exception as e:
        return jsonify({
            'code': 400,
            'message': 'send login code fail',
            'error_info': str(e)
        }), 400

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册接口"""
    try:
        data = request.get_json()
        
        # 验证请求参数
        required_fields = ['username', 'identifier', 'type', 'code', 'password']
        if not data or not all(field in data for field in required_fields):
            return jsonify({
                'code': 400,
                'message': 'create user fail',
                'error_info': 'Missing required parameters'
            }), 400
        
        username = data['username']
        identifier = data['identifier']
        type_ = data['type']
        code = data['code']
        password = data['password']
        
        # 验证标识符格式
        is_valid, error_msg = validate_identifier(identifier, type_)
        if not is_valid:
            return jsonify({
                'code': 400,
                'message': 'create user fail',
                'error_info': error_msg
            }), 400
        
        # 验证验证码
        # if not CaptchaManager.verify_captcha(identifier, code):
        #     return jsonify({
        #         'code': 400,
        #         'message': 'create user fail',
        #         'error_info': 'Invalid or expired verification code'
        #     }), 400
        
        # 检查用户是否已存在
        if type_ == 'phone':
            existing_user = User.query.filter_by(phone_number=identifier).first()
        else:  # email
            existing_user = User.query.filter_by(email=identifier).first()
        
        if existing_user:
            return jsonify({
                'code': 400,
                'message': 'create user fail',
                'error_info': f'User with this {type_} already exists'
            }), 400
        
        # 创建新用户
        new_user = User(username=username, password=password)
        
        if type_ == 'phone':
            new_user.phone_number = identifier
        else:  # email
            new_user.email = identifier
        
        db.session.add(new_user)
        db.session.commit()
        user_dict = new_user.to_dict()
        return jsonify({
            'code': 201,
            'message': 'create user success',
            'user_id': user_dict['id']
        }), 201
        
    except Exception as e:
        return jsonify({
            'code': 400,
            'message': 'create user fail',
            'error_info': str(e)
        }), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录接口"""
    try:
        data = request.get_json()
        
        # 验证请求参数
        if not data or 'identifier' not in data or 'type' not in data:
            return jsonify({
                'code': 401,
                'message': 'user login fail',
                'error_info': 'Missing required parameters'
            }), 401
        
        identifier = data['identifier']
        type_ = data['type']
        
        # 验证标识符格式
        is_valid, error_msg = validate_identifier(identifier, type_)
        if not is_valid:
            return jsonify({
                'code': 401,
                'message': 'user login fail',
                'error_info': error_msg
            }), 401
        
        # 查找用户
        if type_ == 'phone':
            user = User.query.filter_by(phone_number=identifier).first()
        else:  # email
            user = User.query.filter_by(email=identifier).first()
        
        if not user:
            return jsonify({
                'code': 401,
                'message': 'user login fail',
                'error_info': 'User not found'
            }), 401
        
        # 密码登录
        if 'password' in data:
            if not user.check_password(data['password']):
                return jsonify({
                    'code': 401,
                    'message': 'user login fail',
                    'error_info': 'Invalid password'
                }), 401
        # 验证码登录
        elif 'code' in data:
            if not CaptchaManager.verify_captcha(identifier, data['code']):
                return jsonify({
                    'code': 401,
                    'message': 'user login fail',
                    'error_info': 'Invalid or expired verification code'
                }), 401
        else:
            return jsonify({
                'code': 401,
                'message': 'user login fail',
                'error_info': 'Either password or verification code is required'
            }), 401
        
        # 更新最后登录时间
        user.update_last_login()
        user_info = user.to_dict()
        user_id = user_info['id']
        access_token = create_access_token(identity=user_id)
        refresh_token = create_refresh_token(identity=user_id)
        return jsonify({
            'code': 200,
            'message': 'user login success',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user_id': user_id,
            'username': user_info['username'],
            'avatar_url': user_info['avatar_url'],
            'phone': user_info['phone_number'],
            'email': user_info['email']
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 401,
            'message': 'user login fail',
            'error_info': str(e)
        }), 401

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """刷新令牌接口"""
    try:
        # 获取当前用户身份
        current_user_id = get_jwt_identity()
        
        # 创建新的令牌
        access_token = create_access_token(identity=current_user_id)
        refresh_token = create_refresh_token(identity=current_user_id)
        
        return jsonify({
            'code': 200,
            'message': 'token refreshed',
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200
        
    except Exception as e:
        print(e)
        return jsonify({
            'code': 400,
            'message': 'Invalid refresh token',
            'error_info': str(e)
        }), 400