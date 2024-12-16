from datetime import time
from datetime import datetime

# Market Hours
TW_MARKET_START = "09:00"
TW_MARKET_END = "13:35"
US_MARKET_SUMMER_START = "21:30"
US_MARKET_SUMMER_END = "04:00"
US_MARKET_WINTER_START = "22:30"
US_MARKET_WINTER_END = "05:00"

# Market Types
MARKET_TW = "TW"
MARKET_US = "US"

# Stock Exchange Suffixes
TWO_SUFFIX = ":TWO"
TPE_SUFFIX = ":TPE"
NASDAQ_SUFFIX = ":NASDAQ"

# API Endpoints
FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"
DATASETS = {
    "US_MINUTE": "USStockPriceMinute",
    "US_DAILY": "USStockPrice",
    "TW_DAILY": "TaiwanStockPrice"
}

# Time Formats
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"

# Scheduler Settings
SCHEDULER_TIMEZONE = "Asia/Taipei"
UPDATE_INTERVAL = "*/5"  # 每5分鐘