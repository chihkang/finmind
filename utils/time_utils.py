# utils/time_utils.py
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import time
from utils.logger import get_logger

logger = get_logger(__name__)

# 設定默認時區
DEFAULT_TIMEZONE = ZoneInfo("Asia/Taipei")

def setup_timezone():
    """設定時區"""
    if not os.getenv('TZ'):
        os.environ['TZ'] = 'Asia/Taipei'
        try:
            time.tzset()
        except AttributeError:
            logger.warning("Windows 系統不支援 time.tzset()")

def get_current_time():
    """獲取當前時間（確保是台北時間）"""
    return datetime.now(DEFAULT_TIMEZONE)

# 初始化時區
setup_timezone()