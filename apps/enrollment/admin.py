# apps/enrollment/admin.py

"""
学员报名 Admin 配置

包含：
- EnrollmentAdmin（含批量导入自定义按钮 + 导入页面）
- ImportErrorLogAdmin（只读）

批量导入流程：
  Enrollment 列表页 → [批量导入] 按钮 → 选择班级 + 上传 Excel → 同步导入 → 展示结果
"""

import os
import uuid
import tempfile
from django.urls import path
from django.shortcuts import render
from django.contrib import messages
from django import forms
from django.utils import timezone
from django.contrib import admin
from django.contrib.admin import action as admin_action
from .models import Enrollment, ImportErrorLog
from .services import ImportService
from apps.training.models import TrainingClass
from apps.training.enums import ClassStatus


# =============================================================================
# 批量导入表单
# =============================================================================

class ImportEnrollmentForm(forms.Form):
    """批量导入表单 — 班级下拉框 + 文件上传"""
    training_class = forms.ModelChoiceField(
        queryset=TrainingClass.objects.filter(status=ClassStatus.ENROLLING).order_by('name'),
        label='所属班级',
        required=True,
        empty_label='—— 请选择班级 ——',
        widget=forms.Select(attrs={'style': 'max-width: 400px;'}),
    )
    file = forms.FileField(
        label='Excel 文件',
        required=True,
        help_text='仅支持 .xlsx 格式。'
                  '标准列：姓名(必填)、身份证号(必填)、手机号、性别、省、市、区、详细地址、紧急联系人、紧急电话',
        widget=forms.FileInput(attrs={'accept': '.xlsx,.xls'}),
    )


# =============================================================================
# Enrollment Admin
# =============================================================================

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """学员报名后台管理（含批量导入自定义按钮）"""
    list_display = ('person', 'training_class', 'enrollment_status', 'enrolled_at', 'checked_in_at')
    list_filter = ('enrollment_status', 'training_class')
    search_fields = ('person__name', 'person__id_card', 'training_class__name')
    ordering = ('-enrolled_at',)
    readonly_fields = ('enrolled_at', 'checked_in_at', 'created_at')
    actions = ['batch_check_in']
    # ---------- 自定义列表页模板（增加"批量导入"按钮） ----------
    change_list_template = 'admin/enrollment/change_list.html'

    # ================================================================
    # 批量报到 action
    # ================================================================
    @admin_action(description='✅批量报到确认')
    def batch_check_in(self, request, queryset):
        """
        批量将学员报名状态转为「已报到」

        前置校验：
        - 仅允许班级状态为 ENROLLING / ROSTER_GENERATED / SUBMITTED / PENDING_APPROVAL / APPROVED
        - 如果选中记录涉及任何状态不合法的班级，整批拒绝（防止局部成功导致数据混乱）

        幂等性：
        - 已是 CHECKED_IN 的学员自动忽略，不更新 checked_in_at
        """
        allowed_statuses = {
            'ENROLLING', 'ROSTER_GENERATED',
            'SUBMITTED', 'PENDING_APPROVAL', 'APPROVED',
        }

        # ---- 1. 查出选中记录涉及的所有班级 ----

        involved_class_ids = set(
            queryset.values_list('training_class_id', flat=True).distinct()
        )
        invalid_classes = TrainingClass.objects.filter(
            pk__in=involved_class_ids,
        ).exclude(status__in=allowed_statuses)

        # ---- 2. 如果有不合法班级，整批拒绝 ----

        if invalid_classes.exists():
            names = list(invalid_classes.values_list('name', flat=True))
            self.message_user(
                request,
                '❌ 选中记录涉及以下状态不允许报到的班级：\n'
                + '\n'.join(f'  · {name}' for name in names)
                + '\n仅 [报名中/名册已生成/已递交/待审批/已审批] 状态的班级可报到，'
                  '请重新选择。',
                level=messages.ERROR,
            )
            return
            # 整批拒绝，不做任何修改

        # ---- 3. 统计并执行 ----

        total_selected = queryset.count()
        already_checked = queryset.filter(
            enrollment_status=Enrollment.EnrollmentStatus.CHECKED_IN,
        ).count()
        to_update_qs = queryset.filter(
            enrollment_status=Enrollment.EnrollmentStatus.ENROLLED,
        )
        updated_count = to_update_qs.update(
            enrollment_status=Enrollment.EnrollmentStatus.CHECKED_IN,
            checked_in_at=timezone.now(),
        )

        # ---- 4. 结果反馈 ----

        parts = [f'✅ 成功报到 {updated_count} 名学员']
        if already_checked:
            parts.append(f'（{already_checked} 名已报到，幂等忽略）')
        if total_selected - updated_count - already_checked > 0:
            # 有 WITHDRAWN 或其他状态的被跳过

            skipped = total_selected - updated_count - already_checked
            parts.append(f'⚠️ {skipped} 名因状态非 ENROLLED 被跳过')
        self.message_user(request, '，'.join(parts), level=messages.SUCCESS)


    # ---------- 自定义 URL ----------
    def get_urls(self):
        """添加批量导入页面的 URL"""
        urls = super().get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        my_urls = [
            path(
                'import-enrollments/',
                self.admin_site.admin_view(self.import_view),
                name='%s_%s_import' % info,
            ),
        ]
        return my_urls + urls

    # ---------- 批量导入视图 ----------

    def import_view(self, request):
        """
        批量导入页面

        GET  — 显示班级下拉框 + 文件上传表单
        POST — 接收文件，同步调用 ImportService.run_import()，展示结果
        """
        result = None

        if request.method == 'POST':
            form = ImportEnrollmentForm(request.POST, request.FILES)
            if form.is_valid():
                training_class = form.cleaned_data['training_class']
                uploaded_file = request.FILES['file']

                # 校验文件扩展名
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                if ext not in ('.xlsx', '.xls'):
                    messages.error(request, '仅支持 .xlsx / .xls 格式')
                    return render(request, 'admin/enrollment/import_enrollments.html', {
                        'form': form,
                        'result': None,
                        'title': '批量导入学员',
                        'opts': self.model._meta,
                    })

                # 保存上传文件到临时路径
                temp_path = None
                try:
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(
                        temp_dir, f'import_{uuid.uuid4().hex}{ext}',
                    )
                    with open(temp_path, 'wb') as f:
                        for chunk in uploaded_file.chunks():
                            f.write(chunk)

                    # 同步调用 ImportService（该方法本身是同步的，之前被 Django-Q 包装）
                    result = ImportService.run_import(
                        class_id=str(training_class.id),
                        file_path=temp_path,
                        task_id=f'admin_{uuid.uuid4().hex}',
                    )

                    # Django Admin 顶部消息提示
                    if result['success'] > 0:
                        msg = f'✅ 成功导入 {result["success"]} 名学员'
                        if result['fail'] > 0:
                            msg += f'，{result["fail"]} 行失败（详见下方错误明细）'
                        messages.success(request, msg)
                    else:
                        messages.warning(request, f'⚠️ 全部失败，共 {result["fail"]} 行错误')

                except Exception as e:
                    messages.error(request, f'导入异常：{str(e)}')
                    result = None
                finally:
                    # 兜底清理临时文件（ImportService.run_import 末尾也会删除）
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except OSError:
                            pass

                # 导入完成后重新生成空表单
                form = ImportEnrollmentForm()

        else:
            form = ImportEnrollmentForm()

        context = {
            'form': form,
            'result': result,
            'title': '批量导入学员',
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request),
        }
        return render(request, 'admin/enrollment/import_enrollments.html', context)


# =============================================================================
# ImportErrorLog Admin（只读）
# =============================================================================

@admin.register(ImportErrorLog)
class ImportErrorLogAdmin(admin.ModelAdmin):
    """导入错误日志（只读，仅用于查看）"""
    list_display = ('task_id', 'row_num', 'error_type', 'error_message', 'created_at')
    list_filter = ('error_type',)
    search_fields = ('task_id',)
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False