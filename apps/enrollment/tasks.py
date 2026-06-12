# apps/enrollment/tasks.py

"""
学员报名 Django-Q 异步任务

- import_enrollments_task  — 批量导入（被 Django-Q 异步调度）
- get_import_result        — 查询导入结果（供前端轮询）
"""

from loguru import logger
from .services import ImportService
from .models import ImportErrorLog


def import_enrollments_task(class_id: str, file_path: str, task_id: str = None) -> dict:
    """
    批量导入异步任务（由 Django-Q 调用）

    :param class_id:   班级 UUID
    :param file_path:  上传的 Excel 文件路径
    :param task_id:    任务 ID（Django-Q 自动注入）
    :returns: {
        'task_id': str,
        'total': int,
        'success': int,
        'fail': int,
        'errors': list[dict],
    }
    """
    actual_task_id = task_id or 'manual'
    logger.info(f'Django-Q 任务启动：import_enrollments_task [{actual_task_id}]')

    try:
        result = ImportService.run_import(
            class_id=class_id,
            file_path=file_path,
            task_id=actual_task_id,
        )
        return result
    except Exception as e:
        logger.opt(exception=True).error(f'批量导入任务异常 [{actual_task_id}]：{e}')
        return {
            'task_id': actual_task_id,
            'total': 0,
            'success': 0,
            'fail': 1,
            'errors': [{'row_num': 0, 'error_type': 'TASK_FAILED', 'error_message': str(e), 'raw_data': {}}],
        }


def get_import_result(task_id: str) -> dict:
    """
    查询导入结果（供前端轮询）

    :param task_id: Django-Q 任务 ID
    :returns: {
        'task_id': str,
        'total_rows': int,
        'success_count': int,
        'error_count': int,
        'errors': list[dict],
    }
    """
    errors = ImportErrorLog.objects.filter(task_id=task_id)
    error_list = list(errors.values('row_num', 'error_type', 'error_message'))

    return {
        'task_id': task_id,
        'total_rows': error_list[0].get('total', 0) if error_list else 0,
        'success_count': error_list[0].get('success', 0) if error_list else 0,
        'error_count': errors.count(),
        'errors': error_list,
    }