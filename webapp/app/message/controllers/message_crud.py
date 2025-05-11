from flask import request, jsonify, g, Response, stream_with_context
from app.models.message_model import Message
from app.models.conversation_model import Conversation
from app.models.ai_role_model import AIRole
from app import db
import uuid
import requests
from datetime import datetime
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.services.aliyun_api import aliyun_service
import json
import logging

logger = logging.getLogger(__name__)

@jwt_required()
def send_message():
    """发送消息并获取AI回复（流式）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        # 检查必需参数
        required_params = ['conversation_id', 'content', 'type']
        for param in required_params:
            if param not in data:
                return jsonify({"code": 400, "message": f"缺少必要参数：{param}"}), 400
        
        # 获取用户ID
        user_id = get_jwt_identity()
        
        # 获取会话
        conversation: Conversation = Conversation.query.filter_by(
            conversation_id=uuid.UUID(data['conversation_id']).bytes
        ).first()
        
        if not conversation:
            return jsonify({"code": 404, "message": "会话不存在"}), 404
            
        # 验证用户是否有权限操作该会话
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
        
        # 更新会话的最后消息和时间（用户消息）
        conversation.last_message = data['content']
        conversation.last_message_time = datetime.utcnow()
        
        db.session.flush()  # 获取message_id，但不提交事务
        
        # 获取历史消息 (最多30条)
        history_messages = Message.query.filter_by(
            conversation_id=uuid.UUID(data['conversation_id']).bytes
        ).order_by(Message.created_at.desc()).limit(30).all()
        
        # 按时间顺序排列
        history_messages.reverse()
        
        # 准备消息列表，先添加系统角色设定
        messages = []
        
        # 获取AI角色的系统提示
        role: AIRole = AIRole.query.filter_by(
            role_id=conversation.role_id
        ).first()
        if role:
            match role.gender:
                case "male":
                    gender_str = "你是一个男性。"
                case "female":
                    gender_str = "你是一个女性。"
                case "other":
                    gender_str = "你可以是任何性别。"
            age_str = "" if role.age is None else f"你的年龄是：{role.age}岁。"
            response_language = "中文" if role.response_language == "chinese" else "英文"
            system_prompt = f"""
                你将按照以下要求扮演角色与用户对话。
                你的名字:{role.name}。
                {gender_str}{age_str}
                你的性格要求:{role.personality}。
                你应该使用{response_language}与用户交流。
            """
            messages.append({
                "role": "system", 
                "content": [{"text": system_prompt}]
            })
        
        # 添加历史消息
        for msg in history_messages:
            role = "user" if msg.is_user else "assistant"
            messages.append({
                "role": role,
                "content": msg.content
            })
        
        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": data['content']
        })
        
        # 设置响应为流式响应
        ai_message = None
        ai_content = ""
        
        def generate():
            nonlocal ai_content
            nonlocal ai_message
            
            # 创建AI回复消息，初始化为空内容
            ai_message = Message(
                conversation_id=data['conversation_id'],
                type='text',  # AI回复默认为文本类型
                content="",
                is_user=False
            )
            
            db.session.add(ai_message)
            
            # 注意这里先提交，保证消息实体存在，但内容后续更新
            db.session.commit()
            
            # 预先发送一个开始标记
            yield json.dumps({
                "code": 200, 
                "message": "开始生成", 
                "data": {
                    "ai_message_id": ai_message.message_id_str,
                    "chunk": "",
                    "is_last": False
                }
            }) + "\n"
            
            # 定义处理回调的函数
            def on_text_chunk(text_chunk, is_last):
                nonlocal ai_content
                ai_content += text_chunk
                
                response_data = {
                    "code": 200,
                    "message": "生成中" if not is_last else "生成完成",
                    "data": {
                        "ai_message_id": ai_message.message_id_str,
                        "chunk": text_chunk,
                        "is_last": is_last
                    }
                }
                
                return json.dumps(response_data) + "\n"
            
            # 使用aliyun_service调用流式文本对话API
            try:
                # 处理每个文本块
                def handle_stream_callback(text_chunk, is_last):
                    response_json = on_text_chunk(text_chunk, is_last)
                    yield response_json
                    
                    # 如果是最后一个块，更新数据库中的消息内容和会话信息
                    if is_last:
                        try:
                            # 获取AI消息并更新内容
                            ai_msg = Message.query.filter_by(
                                message_id=uuid.UUID(ai_message.message_id_str).bytes
                            ).first()
                            
                            if ai_msg:
                                ai_msg.content = ai_content
                                
                                # 更新会话的最后消息和时间
                                conversation.last_message = ai_content
                                conversation.last_message_time = datetime.utcnow()
                                
                                db.session.commit()
                                logger.info(f"已更新消息记录：{ai_message.message_id_str}")
                        except Exception as e:
                            logger.error(f"更新消息记录失败: {str(e)}")
                            db.session.rollback()
                
                # 调用阿里云服务
                for chunk_response in aliyun_service.text_chat_stream(
                    messages=messages,
                    stream_callback=handle_stream_callback
                ):
                    yield chunk_response
                    
            except Exception as e:
                logger.error(f"AI服务调用失败: {str(e)}")
                error_msg = {
                    "code": 500,
                    "message": f"AI服务调用失败: {str(e)}",
                    "data": {
                        "ai_message_id": ai_message.message_id_str if ai_message else None,
                        "chunk": f"生成失败: {str(e)}",
                        "is_last": True
                    }
                }
                yield json.dumps(error_msg) + "\n"
                
                # 更新错误消息到数据库
                if ai_message:
                    ai_message.content = f"生成失败: {str(e)}"
                    db.session.commit()
        
        return Response(
            stream_with_context(generate()),
            mimetype='application/x-ndjson'
        )
        
    except Exception as e:
        logger.error(f"处理消息时出错: {str(e)}")
        db.session.rollback()
        return jsonify({"code": 500, "message": f"服务器错误: {str(e)}"}), 500

@jwt_required()
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
        conversations_dict = {}
        conversations = Conversation.query.filter(
            Conversation.conversation_id.in_(conversation_ids)
        ).all()
        
        # 检查用户是否有权限删除这些消息
        user_id = get_jwt_identity()
        for conversation in conversations:
            if conversation.user_id != uuid.UUID(user_id).bytes:
                return jsonify({"code": 403, "message": "无权删除部分消息"}), 403
            conversations_dict[conversation.conversation_id] = conversation
        
        # 删除消息
        for message in messages:
            db.session.delete(message)
        
        # 更新各会话的最后一条消息
        for conversation_id in conversation_ids:
            conversation = conversations_dict.get(conversation_id)
            if conversation:
                # 查询这个会话的最后一条消息
                last_message = Message.query.filter_by(
                    conversation_id=conversation_id
                ).order_by(Message.created_at.desc()).first()
                
                if last_message:
                    # 更新会话的最后消息
                    conversation.last_message = last_message.content
                    conversation.last_message_time = last_message.created_at
                else:
                    # 如果会话没有消息了，清空最后消息
                    conversation.last_message = None
                    conversation.last_message_time = None
        
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