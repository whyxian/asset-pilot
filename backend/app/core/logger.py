"""统一日志模块"""

import logging

logger = logging.getLogger("assetpilot")
logger.setLevel(logging.INFO)

_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
))
logger.addHandler(_handler)
