"""自定义业务异常"""


class BusinessError(Exception):
    """业务逻辑异常，由全局异常处理器捕获并返回统一格式"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
