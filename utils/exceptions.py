# utils/exceptions.py

"""
全局异常处理器与错误码定义

用法：
  raise AUTH_TOKEN_MISSING
  raise APIException(code='E-VALID-01', message='身份证号格式错误')

错误码格式：E-模块前缀-两位序号
"""

from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.response import Response


class APIException(Exception):
    """统一异常基类"""
    status_code = 400
    default_code = 'E-SYS-01'
    default_message = '系统内部错误'

    def __init__(self, code=None, message=None):
        self.code = code or self.default_code
        self.message = message or self.default_message


# ========== 认证异常（401） ==========
AUTH_TOKEN_MISSING      = APIException(code='E-AUTH-01', message='未提供认证令牌')
AUTH_TOKEN_EXPIRED      = APIException(code='E-AUTH-02', message='认证令牌已过期')
AUTH_WX_LOGIN_FAILED    = APIException(code='E-AUTH-03', message='微信登录失败')

# ========== 权限异常（403） ==========
PERM_CLASS_EDIT_DENIED  = APIException(code='E-PERM-01', message='无权编辑该班级')
PERM_ATTENDANCE_EDIT    = APIException(code='E-PERM-02', message='无权限修改考勤记录')
PERM_LEAVE_APPROVE      = APIException(code='E-PERM-03', message='无权限审批该请假')

# ========== 参数校验异常（400） ==========
VALID_ID_CARD_FORMAT    = APIException(code='E-VALID-01', message='身份证号格式错误')
VALID_ID_CARD_DUPLICATE = APIException(code='E-VALID-02', message='该身份证号已存在')
VALID_DATE_RANGE        = APIException(code='E-VALID-03', message='结束日期不得早于开始日期')

# ========== 班级业务异常（409/422） ==========
CLS_STATUS_INVALID      = APIException(code='E-CLS-01', message='不允许的状态转换')
CLS_CLASS_FULL          = APIException(code='E-CLS-02', message='班级已满员')
CLS_ROSTER_LOCKED       = APIException(code='E-CLS-03', message='名单已锁定不可修改')
CLS_ARCHIVED            = APIException(code='E-CLS-04', message='已归档不可修改')
CLS_CONCURRENT          = APIException(code='E-CLS-05', message='并发状态修改')

# ========== 报名业务异常（409/422） ==========
ENR_DUPLICATE           = APIException(code='E-ENR-01', message='该学员已在本班级报名')
ENR_NOT_CHECKED_IN      = APIException(code='E-ENR-02', message='学员未报到，无法操作')

# ========== 请假业务异常（409/422） ==========
LVE_CONFLICT            = APIException(code='E-LVE-01', message='请假日期与已有请假记录冲突')
LVE_NO_COURSE           = APIException(code='E-LVE-02', message='请假日期范围内无课程安排')
LVE_ALREADY_DECIDED     = APIException(code='E-LVE-03', message='请假已审批，不可重复审批')
LVE_DUPLICATE           = APIException(code='E-LVE-04', message='重复请假')
LVE_APPROVED_ATTENDANCE = APIException(code='E-LVE-05', message='审批通过考勤联动')
LVE_REJECTED_ATTENDANCE = APIException(code='E-LVE-06', message='审批拒绝考勤联动')

# ========== 考勤异常（409） ==========
ATT_CONFLICT            = APIException(code='E-ATT-01', message='并发修改考勤，数据已变更')
ATD_ABSENT              = APIException(code='E-ATD-01', message='未签到未请假')
ATD_MODIFY_ERROR        = APIException(code='E-ATD-02', message='误操作修改签到')
ATD_NO_RECORD_ADD       = APIException(code='E-ATD-03', message='无签到记录时特殊新增学员')
ATD_HAS_RECORD_REVERT   = APIException(code='E-ATD-04', message='有签到记录时无法回退')

# ========== 批量导入异常（409） ==========
BAT_FORMAT_ERROR        = APIException(code='E-BAT-01', message='Excel某行格式错误')
BAT_ID_CARD_FORMAT      = APIException(code='E-BAT-02', message='身份证号格式错误')
BAT_ID_CARD_DUPLICATE   = APIException(code='E-BAT-03', message='身份证号重复(同一班级内)')
BAT_CLASS_STATUS_INVALID = APIException(code='E-BAT-04', message='班级状态不允许导入')
BAT_FILE_EMPTY          = APIException(code='E-BAT-05', message='文件为空')
BAT_FILE_FORMAT         = APIException(code='E-BAT-06', message='文件格式不支持')

# ========== 并发操作（409） ==========
CNC_CLASS               = APIException(code='E-CNC-01', message='同时修改班级')
CNC_IMPORT              = APIException(code='E-CNC-02', message='同时导入学员(允许)')
CNC_ID_CARD             = APIException(code='E-CNC-03', message='并发身份证重复')

# ========== 系统异常（500） ==========
SYS_INTERNAL_ERROR      = APIException(code='E-SYS-01', message='系统内部错误')
SYS_DATABASE_ERROR      = APIException(code='E-SYS-02', message='数据库操作失败')
SYS_TASK_FAILED         = APIException(code='E-SYS-03', message='异步任务执行失败')


def custom_exception_handler(exc, context):
    """
    全局异常处理器：
    1. 捕获 ValidationError、PermissionDenied、APIException、Exception
    2. 统一返回 {"code": "XXX", "message": "...", "data": null}
    """
    response = exception_handler(exc, context)

    if response is not None:
        data = response.data
        if isinstance(data, dict):
            code = data.get('code', exc.default_code if hasattr(exc, 'default_code') else 'SYS_INTERNAL_ERROR')
            message = data.get('message', str(exc))
        elif isinstance(data, list):
            code = 'VALID_PARAMS'
            message = '; '.join(str(item) for item in data)
        else:
            code = 'SYS_INTERNAL_ERROR'
            message = str(data)

        response.data = {
            'code': code,
            'message': message,
            'data': None
        }

    else:
        # 未被 DRF 捕获的异常
        import traceback
        from loguru import logger
        logger.opt(exception=True).error(f"Unhandled exception: {exc}")

        response = Response(
            {'code': 'SYS_INTERNAL_ERROR', 'message': '系统内部错误', 'data': None},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response