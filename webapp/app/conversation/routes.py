from app.conversation import conversation_bp
from .controllers.conversation_crud import create_conversation, update_conversation, delete_conversation
from .controllers.conversation_list import get_user_role_conversations

# 创建会话相关路由
conversation_bp.route('/create_conversation', methods=['POST'])(create_conversation)

# 查询用户与特定角色的所有会话
conversation_bp.route('/get_user_role_conversations', methods=['POST'])(get_user_role_conversations)

# 删除会话相关路由
conversation_bp.route('/delete_conversation', methods=['POST'])(delete_conversation)

# 修改会话相关路由
conversation_bp.route('/update_conversation', methods=['POST'])(update_conversation) 