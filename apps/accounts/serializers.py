# apps/accounts/serializers.py

"""
认证模块序列化器
- LoginSerializer:     账号密码登录（教职员工）
- WxLoginSerializer:  微信登录（学员）
- SmsLoginSerializer: 短信验证码登录（学员）
- TokenRefreshSerializer: 刷新 Token（使用 SimpleJWT 默认实现，仅重导出）
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from .models import User
from .authentication import CustomTokenObtainPairSerializer


class LoginSerializer(serializers.Serializer):
    """
    账号密码登录序列化器

    POST /api/v1/auth/login/
    请求体：{ "username": "xxx", "password": "xxx" }
    响应体：{ "access": "xxx", "refresh": "xxx", "user": { ... } }
    """

    username = serializers.CharField(max_length=150, write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    # 只读输出字段
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user_info = serializers.SerializerMethodField(read_only=True, method_name='get_user_info')

    def validate(self, attrs):
        """
        校验用户名密码
        使用 Django 的 authenticate() 方法，支持扩展认证后端
        """
        username = attrs.get('username')
        password = attrs.get('password')

        # authenticate 会检查 User.is_active
        user = authenticate(username=username, password=password)

        if user is None:
            # 不区分「用户不存在」和「密码错误」，防止用户名枚举攻击
            raise serializers.ValidationError('用户名或密码错误', code='E-AUTH-01')

        # 生成 JWT Token
        # 使用 CustomTokenObtainPairSerializer 注入 role 等自定义 claims
        token_serializer = CustomTokenObtainPairSerializer()
        token = token_serializer.get_token(user)
        refresh_token = str(token)
        access_token = str(token.access_token)

        return {
            'access': access_token,
            'refresh': refresh_token,
            'user_info': {
                'id': str(user.id),
                'username': user.username,
                'role': user.role,
                'role_display': user.role_display,
            },
        }

    def get_user_info(self, obj):
        return obj.get('user_info')


class WxLoginSerializer(serializers.Serializer):
    """
    微信一键登录序列化器（学员端）

    流程：
    1. 前端调微信登录获取 code
    2. 后端用 code 换 openid（调用微信服务器）
    3. 根据 openid 查找或创建 Person 记录
    4. 生成 JWT Token（role=STUDENT，person_id 替代 user_id）

    请求体：{ "code": "xxx" }
    """

    code = serializers.CharField(write_only=True, max_length=200)

    # JWT Token 输出
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    is_new_user = serializers.BooleanField(read_only=True, default=False)

    def validate(self, attrs):
        """
        校验微信登录 code

        注意：当前返回模拟数据，集成微信登录后应：
        1. 调用 https://api.weixin.qq.com/sns/jscode2session
        2. 获取 openid 和 session_key
        3. 根据 openid 查找/创建 Person 记录
        """
        code = attrs.get('code')

        # ========== 模拟微信登录（开发调试用）==========
        # TODO: 集成微信小程序登录后替换此段
        # 微信服务器返回示例：{"openid": "oXXXX-xxx", "session_key": "xxxx"}
        # 真实集成时使用 requests.post 调用微信接口
        mock_openid = f'mock_openid_{code[:8]}' if len(code) > 8 else 'mock_openid_dev'
        # ============================================

        # 通过 openid 查找已有 Person
        # 注意：Person 模型在 apps.persons 中，字段名为 openid
        from apps.persons.models import Person

        try:
            person = Person.objects.get(openid=mock_openid)
            is_new = False
        except Person.DoesNotExist:
            # 新用户，先创建 Person（部分信息需后续补充）
            person = Person.objects.create(
                openid=mock_openid,
                name='微信用户',  # 临时名称，可后续修改
            )
            is_new = True

        # 生成 JWT Token（学员 Token）
        # 学员没有 User 记录，使用自定义 Token 工厂
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken()
        refresh['person_id'] = str(person.id)
        refresh['role'] = 'STUDENT'
        refresh['openid'] = mock_openid

        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'is_new_user': is_new,
        }


class SmsLoginSerializer(serializers.Serializer):
    """
    手机号 + 短信验证码登录序列化器（学员端）

    流程：
    1. 前端获取手机号和短信验证码
    2. 后端校验验证码（需集成短信服务）
    3. 根据手机号查找或创建 Person 记录
    4. 生成 JWT Token

    请求体：{ "phone": "13800138000", "sms_code": "123456" }
    """

    phone = serializers.CharField(max_length=20, write_only=True)
    sms_code = serializers.CharField(max_length=6, write_only=True)

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    is_new_user = serializers.BooleanField(read_only=True, default=False)

    def validate(self, attrs):
        phone = attrs.get('phone')
        sms_code = attrs.get('sms_code')

        # ========== 模拟短信校验（开发调试用）==========
        # TODO: 集成真实短信服务后替换
        # 真实逻辑：调用短信服务验证 sms_code 是否匹配
        if sms_code != '123456' and sms_code != '000000':
            raise serializers.ValidationError('验证码错误', code='E-AUTH-03')
        # ============================================

        # 通过手机号查找已有 Person
        from apps.persons.models import Person

        try:
            person = Person.objects.filter(phone=phone).first()
            is_new = False
            if person is None:
                # 手机号未注册，创建新 Person
                person = Person.objects.create(
                    phone=phone,
                    name='学员',  # 临时名称
                )
                is_new = True
        except Exception:
            raise serializers.ValidationError('登录失败，请重试', code='E-AUTH-03')

        # 生成 JWT Token（学员 Token）
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken()
        refresh['person_id'] = str(person.id)
        refresh['role'] = 'STUDENT'
        refresh['phone'] = phone

        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'is_new_user': is_new,
        }


class TokenRefreshResponseSerializer(serializers.Serializer):
    """
    Token 刷新响应序列化器
    用于 API 文档展示，实际使用 SimpleJWT 自带的 TokenRefreshView
    """

    access = serializers.CharField(read_only=True)