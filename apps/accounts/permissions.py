# apps/accounts/permissions.py

"""
角色权限类
基于 JWT Token 中的 role 字段判断权限

使用示例：
    class ClassListView(APIView):
        permission_classes = [IsAuthenticated, IsTeachingAdmin]

注意：
    - 学员权限不是通过 PermissionClass 控制，而是通过 Enrollment 关联判断
    - 学员端 API 统一使用 IsStudentFromEnrollment 自定义权限
"""

from rest_framework.permissions import BasePermission


class IsTeachingAdmin(BasePermission):
    """仅教学管理员（ADMIN）"""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'ADMIN'
        )


class IsTeacher(BasePermission):
    """仅教学人员（TEACHER）"""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'TEACHER'
        )


class IsPrincipal(BasePermission):
    """仅校长（PRINCIPAL）"""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'PRINCIPAL'
        )


class IsTeachingStaff(BasePermission):
    """
    教学人员及以上（TEACHER / ADMIN / PRINCIPAL）
    用于考勤录入等教学人员和教学管理员都可操作的功能
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('TEACHER', 'ADMIN', 'PRINCIPAL')
        )


class IsAdminOrPrincipal(BasePermission):
    """
    教学管理员或校长（ADMIN / PRINCIPAL）
    用于请假审批（>2天）等需要校长权限的场景
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('ADMIN', 'PRINCIPAL')
        )