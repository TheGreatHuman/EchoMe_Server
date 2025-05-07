from flask import request, jsonify, g
from app.models.message_model import Message
from app.models.conversation_model import Conversation
from app import db
import uuid
import requests
from datetime import datetime
from app.auth.jwt_auth import jwt_required
from flask_jwt_extended import get_jwt_identity

@jwt_required
def send_message():
    """发送消息并获取AI回复"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        # 检查必需参数
        required_params = ['conversation_id', 'content', 'type']
        for param in required_params:
            if param not in data:
                return jsonify({"code": 400, "message": f"缺少必要参数：{param}"}), 400
        
        # 获取会话
        conversation = Conversation.query.filter_by(
            conversation_id=uuid.UUID(data['conversation_id']).bytes
        ).first()
        
        if not conversation:
            return jsonify({"code": 404, "message": "会话不存在"}), 404
            
        # 验证用户是否有权限操作该会话
        user_id = get_jwt_identity()
        if conversation.user_id != uuid.UUID(user_id).bytes:
            return jsonify({"code": 403, "message": "无权操作此会话"}), 403
        
        # 创建用户消息
        user_message = Message(
            conversation_id=data['conversation_id'],
            type=data['type'],
            content=data['content'],
            is_user=True
        )
        
        db.session.add(user_message)
        db.session.flush()  # 获取message_id，但不提交事务
        
        # 调用外部AI服务获取回复
        ai_response_text = call_external_ai_service(
            conversation_id=data['conversation_id'],
            message=data['content'],
            role_id=conversation.role_id_str
        )
        
        # 创建AI回复消息
        ai_message = Message(
            conversation_id=data['conversation_id'],
            type='text',  # AI回复默认为文本类型
            content=ai_response_text,
            is_user=False
        )
        
        db.session.add(ai_message)
        
        # 更新会话的最后消息和时间
        conversation.last_message = ai_response_text
        conversation.last_message_time = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "code": 200,
            "message": "消息发送成功",
            "data": {
                "user_message": user_message.to_dict(),
                "ai_message": ai_message.to_dict()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"服务器错误: {str(e)}"}), 500

@jwt_required
def delete_messages():
    """删除多条消息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        # 检查必需参数
        if 'message_ids' not in data or not isinstance(data['message_ids'], list):
            return jsonify({"code": 400, "message": "缺少必要参数：消息ID列表"}), 400
            
        if not data['message_ids']:
            return jsonify({"code": 400, "message": "消息ID列表不能为空"}), 400
        
        # 验证所有消息ID格式
        try:
            message_ids_bytes = [uuid.UUID(mid).bytes for mid in data['message_ids']]
        except ValueError:
            return jsonify({"code": 400, "message": "无效的消息ID格式"}), 400
        
        # 获取这些消息
        messages = Message.query.filter(Message.message_id.in_(message_ids_bytes)).all()
        
        if not messages:
            return jsonify({"code": 404, "message": "未找到指定的消息"}), 404
        
        # 获取消息所属的会话，并确保用户有权限
        conversation_ids = set(message.conversation_id for message in messages)
        conversations = Conversation.query.filter(
            Conversation.conversation_id.in_(conversation_ids)
        ).all()
        
        # 检查用户是否有权限删除这些消息
        user_id = get_jwt_identity()
        for conversation in conversations:
            if conversation.user_id != uuid.UUID(user_id).bytes:
                return jsonify({"code": 403, "message": "无权删除部分消息"}), 403
        
        # 删除消息
        for message in messages:
            db.session.delete(message)
        
        db.session.commit()
        
        return jsonify({
            "code": 200,
            "message": "消息删除成功",
            "data": {
                "deleted_count": len(messages)
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"服务器错误: {str(e)}"}), 500

def call_external_ai_service(conversation_id, message, role_id):
    """调用外部AI服务获取回复
    
    这里是一个示例实现，实际应用中应该调用真实的AI服务
    """
    try:
        # 这里只是一个示例，实际应用中应该配置真实的AI服务URL
        ai_service_url = "http://localhost:8000/api/ai/generate_response"
        
        # 准备请求数据
        request_data = {
            "conversation_id": conversation_id,
            "message": message,
            "role_id": role_id
        }
        
        # 调用外部服务
        response = requests.post(ai_service_url, json=request_data)
        
        # 检查响应状态
        if response.status_code == 200:
            response_data = response.json()
            return response_data.get("response", "AI服务未返回有效回复")
        else:
            # 如果外部服务调用失败，返回错误消息
            return f"AI服务调用失败，错误码: {response.status_code}"
            
    except Exception as e:
        # 在实际应用中应该进行更详细的错误处理和日志记录
        return f"AI服务调用异常: {str(e)}" 