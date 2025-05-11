from . import message_bp
from .controllers.message_crud import send_message, delete_messages
from .controllers.message_list import get_conversation_messages

# 发送消息相关路由
message_bp.route('/send_message', methods=['POST'])(send_message)

# 获取会话的所有消息
message_bp.route('/get_conversation_messages', methods=['POST'])(get_conversation_messages)

# 删除消息相关路由
message_bp.route('/delete_messages', methods=['POST'])(delete_messages) 