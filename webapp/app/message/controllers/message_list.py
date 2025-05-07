from flask import request, jsonify, g
from app.models.message_model import Message
from app.models.conversation_model import Conversation
from app import db
import uuid
from flask_jwt_extended import get_jwt_identity, jwt_required

@jwt_required
def get_conversation_messages():
    """获取会话的所有消息"""
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
            
        # 验证用户是否有权限查看该会话
        user_id = get_jwt_identity()
        if conversation.user_id != uuid.UUID(user_id).bytes:
            return jsonify({"code": 403, "message": "无权查看此会话"}), 403
        
        # 查询会话的所有消息
        messages = Message.query.filter_by(
            conversation_id=conversation.conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        # 转换为字典列表
        messages_data = [message.to_dict() for message in messages]
        
        return jsonify({
            "code": 200,
            "message": "查询成功",
            "data": messages_data
        }), 200
        
    except Exception as e:
        return jsonify({"code": 500, "message": f"服务器错误: {str(e)}"}), 500 