from app.ai_role import ai_role_bp
from .controllers.role_list import get_roles
from .controllers.role_detail import get_role_detail, get_created_roles
from .controllers.role_crud import create_role, update_role, delete_role
from .controllers.user_role_relation import get_user_roles, add_user_role_relation, delete_user_role_relation

# 角色列表相关路由
ai_role_bp.route('/get_roles', methods=['POST'])(get_roles)

# 角色详情相关路由
ai_role_bp.route('/get_role_detail', methods=['POST'])(get_role_detail)

# 角色增删改相关路由
ai_role_bp.route('/create_role', methods=['POST'])(create_role)

ai_role_bp.route('/update_role', methods=['POST'])(update_role)

ai_role_bp.route('/delete_role', methods=['POST'])(delete_role)

# 用户角色关系相关路由
ai_role_bp.route('/get_user_roles', methods=['POST'])(get_user_roles)

ai_role_bp.route('/add_user_role_relation', methods=['POST'])(add_user_role_relation)

ai_role_bp.route('/delete_user_role_relation', methods=['POST'])(delete_user_role_relation)

# 获取用户创建的角色
ai_role_bp.route('/get_created_roles', methods=['GET'])(get_created_roles)
