# apps/accounts/views.py

"""
认证 API 视图
- POST /api/v1/auth/login/       → LoginView（教职员工账号密码登录）
- POST /api/v1/auth/wx-login/    → WxLoginView（学员微信一键登录）
- POST /api/v1/auth/sms-login/   → SmsLoginView（学员手机验证码登录）
- POST /api/v1/auth/refresh/     → TokenRefreshView（刷新 Token，SimpleJWT 内置）

### 为什么登录 API 用 APIView 而不是 ViewSet？
登录是一次性操作，没有列表/详情/更新/删除等 CRUD 语义，APIView 更清晰。
如后续需要批量操作，可迁移至 GenericViewSet。
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import (
    LoginSerializer,
    WxLoginSerializer,
    SmsLoginSerializer,
)


class LoginView(generics.GenericAPIView):
    """
    账号密码登录

    适用角色：教学管理员（ADMIN）/ 教学人员（TEACHER）/ 校长（PRINCIPAL）
    学员请使用 wx-login 或 sms-login。

    POST /api/v1/auth/login/
    {
        "username": "admin",
        "password": "your_password"
    }
    → 200 OK
    {
        "access": "eyJ...",
        "refresh": "eyJ...",
        "user_info": {
            "id": "uuid",
            "username": "admin",
            "role": "ADMIN",
            "role_display": "教学管理员"
        }
    }
    """

    serializer_class = LoginSerializer
    # 登录端点放行（不需要认证）
    permission_classes = [AllowAny]
    # 登录不经过全局异常处理器中的认证检查

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class WxLoginView(generics.GenericAPIView):
    """
    微信一键登录（学员端）

    前置条件：
    - 前端已通过 wx.login() 获取临时 code
    - 后端已配置微信小程序的 AppID 和 AppSecret

    POST /api/v1/auth/wx-login/
    { "code": "wx_code_from_frontend" }
    → 200 OK
    { "access": "eyJ...", "refresh": "eyJ...", "is_new_user": false }

    ### 注意
    当前返回模拟数据。部署前需对接微信服务器（jscode2session）。
    """

    serializer_class = WxLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class SmsLoginView(generics.GenericAPIView):
    """
    手机号 + 短信验证码登录（学员端）

    前置条件：
    - 前端已通过短信服务获取验证码
    - 后端已配置短信服务（阿里云/腾讯云 SMS）

    POST /api/v1/auth/sms-login/
    { "phone": "13800138000", "sms_code": "123456" }
    → 200 OK
    { "access": "eyJ...", "refresh": "eyJ...", "is_new_user": true }

    ### 开发调试
    验证码 123456 或 000000 视为通过（请勿在生产环境使用此逻辑）。
    """

    serializer_class = SmsLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)