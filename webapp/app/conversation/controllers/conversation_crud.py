from flask import request, jsonify, g
from app.models.conversation_model import Conversation
from app.models.message_model import Message
from app import db
import uuid
from datetime import datetime
from flask_jwt_extended import get_jwt_identity, jwt_required

@jwt_required()
def create_conversation():
    """创建新会话"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        # 从JWT中获取用户ID
        user_id = get_jwt_identity()
        
        # 检查必需参数
        if 'role_id' not in data:
            return jsonify({"code": 400, "message": "缺少必要参数：角色ID"}), 400
            
        # 设置title的默认值
        title = data.get('title', '新的聊天')
        
        # 创建会话
        conversation = Conversation(
            role_id=data['role_id'],
            user_id=user_id,
            title=title,
            voice_id=data.get('voice_id'),
            speech_rate=data.get('speech_rate', 10),
            pitch_rate=data.get('pitch_rate', 10)
        )
        
        db.session.add(conversation)
        db.session.commit()
        
        return jsonify({
            "code": 200,
            "message": "会话创建成功",
            "data": conversation.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"服务器错误: {str(e)}"}), 500

@jwt_required()
def update_conversation():
    """更新会话信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        # 检查必需参数
        if 'conversation_id' not in data:
            return jsonify({"code": 400, "message": "缺少必要参数：会话ID"}), 400
        
        # 获取会话
        conversation = Conversation.query.filter_by(
            conversation_id=uuid.UUID(data['conversation_id']).bytes
        ).first()
        
        if not conversation:
            return jsonify({"code": 404, "message": "会话不存在"}), 404
            
        # 验证用户是否有权限修改该会话
        user_id = get_jwt_identity()
        if conversation.user_id != uuid.UUID(user_id).bytes:
            return jsonify({"code": 403, "message": "无权修改此会话"}), 403
        
        # 更新会话信息
        if 'title' in data:
            conversation.title = data['title']
        
        if 'voice_id' in data:
            conversation.voice_id = uuid.UUID(data['voice_id']).bytes if data['voice_id'] else None
            
        if 'speech_rate' in data:
            conversation.speech_rate = data['speech_rate']
            
        if 'pitch_rate' in data:
            conversation.pitch_rate = data['pitch_rate']
        
        db.session.commit()
        
        return jsonify({
            "code": 200,
            "message": "会话更新成功",
            "data": conversation.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"服务器错误: {str(e)}"}), 500

@jwt_required()
def delete_conversation():
    """删除会话及其所有消息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        # 检查必需参数
        if 'conversation_id' not in data:
            return jsonify({"code": 400, "message": "缺少必要参数：会话ID"}), 400
            
        # 获取会话
        conversation = Conversation.query.filter_by(
            conversation_id=uuid.UUID(data['conversation_id']).bytes
        ).first()
        
        if not conversation:
            return jsonify({"code": 404, "message": "会话不存在"}), 404
            
        # 验证用户是否有权限删除该会话
        user_id = get_jwt_identity()
        if conversation.user_id != uuid.UUID(user_id).bytes:
            return jsonify({"code": 403, "message": "无权删除此会话"}), 403
        
        # 删除该会话下的所有消息
        Message.query.filter_by(conversation_id=conversation.conversation_id).delete()
        
        # 删除会话
        db.session.delete(conversation)
        db.session.commit()
        
        return jsonify({
            "code": 200,
            "message": "会话及其消息已成功删除"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"服务器错误: {str(e)}"}), 500 