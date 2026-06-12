# apps/accounts/models.py

"""
用户模型（教职员工账号）
- 学员没有 User 账号，通过微信登录 / 短信验证码登录
- role 枚举：ADMIN（教学管理员）/ TEACHER（教学人员）/ PRINCIPAL（校长）

### 为什么暂时没有 person 字段？
person 字段关联到 apps.persons.Person 模型，该模型将在 T-03 创建。
待 T-03 就绪后，需要通过新 migration 添加 person 字段。
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    """自定义用户管理器 — 支持 create_user / create_superuser"""

    def create_user(self, username: str, password: str = None, **extra_fields):
        """
        创建普通用户
        - username 必填且唯一
        - password 可选（首次可通过后台创建再设密码）
        """
        if not username:
            raise ValueError('用户名不能为空')

        user = self.model(username=username, **extra_fields)
        user.set_password(password)  # 加密密码
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, password: str, **extra_fields):
        """
        创建超级管理员（Django Admin 登录用）
        - 自动设置 role=ADMIN 和 is_staff=True
        """
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('role') != User.Role.ADMIN:
            raise ValueError('超级用户角色必须是 ADMIN')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('超级用户必须设置 is_staff=True')

        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    教职员工账号模型

    ### 为什么继承 AbstractBaseUser 而非 AbstractUser？
    AbstractUser 强制包含 first_name / last_name / email / date_joined 等字段，
    而我们只需要 username + password + role，避免冗余字段。

    ### 为什么学员不创建 User 记录？
    学员通过微信登录（openid）或短信验证码登录（phone），
    验证通过后返回 JWT token，无需维护密码。
    """

    class Role(models.TextChoices):
        """角色枚举 — 与权限矩阵对齐"""
        ADMIN = 'ADMIN', '教学管理员'
        TEACHER = 'TEACHER', '教学人员'
        PRINCIPAL = 'PRINCIPAL', '校长'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID',
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='用户名',
        help_text='登录账号，字母开头，可包含字母/数字/下划线',
    )
    # password 由 AbstractBaseUser 提供（hashed 存储）

    # TODO: T-03 创建 Person 模型后，通过新 migration 添加以下字段
    # person = models.OneToOneField(
    #     'persons.Person',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     verbose_name='关联人员档案',
    # )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN,
        verbose_name='角色',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否启用',
        help_text='禁用后无法登录系统',
    )

    # Django Admin 所需字段
    is_staff = models.BooleanField(
        default=False,
        verbose_name='是否可登录 Admin',
        help_text='设为 True 才能登录 Django Admin 后台',
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    # 重写 PermissionsMixin 继承的 groups 和 user_permissions
    # 使用自定义 related_name 避免与 auth.User 冲突
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='用户组',
        blank=True,
        help_text='用户所属组，组权限会自动继承',
        related_name='accounts_user_set',
        related_query_name='accounts_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='用户权限',
        blank=True,
        help_text='用户的独立权限',
        related_name='accounts_user_set',
        related_query_name='accounts_user',
    )

    # --- 认证配置 ---
    # 用 username 作为登录标识
    USERNAME_FIELD = 'username'
    # createsuperuser 时额外提示的必填字段
    REQUIRED_FIELDS = ['role']

    objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'
        # 按创建时间倒序
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def role_display(self) -> str:
        """返回角色中文名"""
        return self.get_role_display()