# apps/accounts/urls.py

"""
认证模块路由

/api/v1/auth/
├── login/        POST   → 教职员工账号密码登录
├── wx-login/     POST   → 学员微信一键登录
├── sms-login/    POST   → 学员手机验证码登录
└── refresh/      POST   → 刷新 JWT Token
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('wx-login/', views.WxLoginView.as_view(), name='wx-login'),
    path('sms-login/', views.SmsLoginView.as_view(), name='sms-login'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]