# apps/accounts/authentication.py

"""
自定义 JWT Token 认证
- Token 中包含 role 字段，避免每次请求都查数据库
- 学员 Token（wx-login / sms-login）包含 person_id 和 role=STUDENT
"""

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    自定义 JWT Token 序列化器
    - 在 Token payload 中添加 role 和 username
    - 前端可通过解析 Token 直接判断用户角色和权限
    """

    @classmethod
    def get_token(cls, user) -> Token:
        """
        生成 JWT Token 时注入自定义 claims

        Token payload 结构：
        {
            'token_type': 'access',    # 或 'refresh'
            'exp': 1234567890,         # 过期时间
            'iat': 1234567890,         # 签发时间
            'jti': 'xxx',              # Token ID
            'user_id': 'uuid-string',  # 用户 ID
            'username': 'admin',       # 用户名
            'role': 'ADMIN',           # 角色（前端据此控制菜单权限）
        }
        """
        token = super().get_token(user)

        # 注入自定义字段
        token['username'] = user.username
        token['role'] = user.role

        return token