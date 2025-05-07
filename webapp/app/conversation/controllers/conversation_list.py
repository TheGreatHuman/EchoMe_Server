from flask import request, jsonify, g
from app.models.conversation_model import Conversation
from app import db
import uuid
from flask_jwt_extended import get_jwt_identity, jwt_required

@jwt_required
def get_user_role_conversations():
    """获取用户与特定角色的所有会话"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        # 从JWT中获取用户ID
        user_id = get_jwt_identity()
        
        # 检查必需参数
        if 'role_id' not in data:
            return jsonify({"code": 400, "message": "缺少必要参数：角色ID"}), 400
        
        # 查询用户与特定角色的所有会话
        conversations = Conversation.query.filter_by(
            user_id=uuid.UUID(user_id).bytes,
            role_id=uuid.UUID(data['role_id']).bytes
        ).order_by(Conversation.created_at.desc()).all()
        
        # 转换为字典列表
        conversations_data = [conversation.to_dict() for conversation in conversations]
        
        return jsonify({
            "code": 200,
            "message": "查询成功",
            "data": conversations_data
        }), 200
        
    except Exception as e:
        return jsonify({"code": 500, "message": f"服务器错误: {str(e)}"}), 500 