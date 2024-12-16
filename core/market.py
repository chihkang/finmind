from datetime import datetime, timedelta
from config.constants import (
    TW_MARKET_START, TW_MARKET_END,
    US_MARKET_SUMMER_START, US_MARKET_SUMMER_END,
    US_MARKET_WINTER_START, US_MARKET_WINTER_END,
    TIME_FORMAT
)

class MarketTimeChecker:
    @staticmethod
    def is_dst() -> bool:
        """判斷是否為美國夏令時間"""
        now = datetime.now()
        year = now.year
        
        # 計算3月第二個週日
        march = datetime(year, 3, 1)
        march_second_sunday = march + timedelta(days=(13 - march.weekday()))
        
        # 計算11月第一個週日
        november = datetime(year, 11, 1)
        november_first_sunday = november + timedelta(days=(6 - november.weekday()))
        
        return march_second_sunday <= now < november_first_sunday

    @staticmethod
    def is_tw_market_hours() -> bool:
        """判斷是否為台股交易時段"""
        now = datetime.now()
        current_time = now.time()
        start_time = datetime.strptime(TW_MARKET_START, TIME_FORMAT).time()
        end_time = datetime.strptime(TW_MARKET_END, TIME_FORMAT).time()
        
        return start_time <= current_time <= end_time

    @staticmethod
    def is_us_market_hours() -> bool:
        """判斷是否為美股交易時段（台北時間）"""
        now = datetime.now()
        current_time = now.time()
        
        if MarketTimeChecker.is_dst():
            start_time = datetime.strptime(US_MARKET_SUMMER_START, TIME_FORMAT).time()
            end_time = datetime.strptime(US_MARKET_SUMMER_END, TIME_FORMAT).time()
        else:
            start_time = datetime.strptime(US_MARKET_WINTER_START, TIME_FORMAT).time()
            end_time = datetime.strptime(US_MARKET_WINTER_END, TIME_FORMAT).time()
        
        # 跨午夜的情況需要特別處理
        if start_time > end_time:
            return current_time >= start_time or current_time <= end_time
        return start_time <= current_time <= end_time

    @classmethod
    def get_market_hours(cls) -> tuple:
        """獲取當前市場交易時間"""
        if cls.is_dst():
            return US_MARKET_SUMMER_START, US_MARKET_SUMMER_END
        return US_MARKET_WINTER_START, US_MARKET_WINTER_END