from datetime import timedelta
from config.constants import DATE_FORMAT
# 在所有需要使用時間的模組中
from utils.time_utils import get_current_time

class TradingDateCalculator:
    @staticmethod
    def get_last_us_trading_date() -> str:
        """獲取上一個美股交易日的日期"""
        now = get_current_time()
        
        # 如果是週一，回傳上週五的日期
        if now.weekday() == 0:
            last_trading_date = now - timedelta(days=3)
        # 如果是週日，回傳上週五的日期
        elif now.weekday() == 6:
            last_trading_date = now - timedelta(days=2)
        # 其他情況回傳前一天
        else:
            last_trading_date = now - timedelta(days=1)
        
        return last_trading_date.strftime(DATE_FORMAT)

    @staticmethod
    def get_date_range(days: int = 5) -> tuple[str, str]:
        """獲取日期範圍"""
        end_date = get_current_time()
        start_date = end_date - timedelta(days=days)
        return start_date.strftime(DATE_FORMAT), end_date.strftime(DATE_FORMAT)

    @staticmethod
    def is_weekend() -> bool:
        """判斷是否為週末"""
        return get_current_time().weekday() >= 5