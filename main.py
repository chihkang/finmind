from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from core.scheduler import StockScheduler
from core.updater import StockPriceUpdater
from core.market import MarketTimeChecker
from config.settings import HOST, PORT
from utils.logger import get_logger
from utils.time_utils import get_current_time
import os
import time
from datetime import datetime  # 添加這個導入

logger = get_logger(__name__)

# 初始化服務
updater = StockPriceUpdater()
scheduler = StockScheduler()

# 驗證時區設定
current_time = get_current_time()
system_time = datetime.now()
logger.info(f"系統時區: {time.tzname}")
logger.info(f"系統時間: {system_time}")
logger.info(f"設定後的台北時間: {current_time}")
logger.info(f"環境變數TZ: {os.getenv('TZ')}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """處理應用程式的生命週期事件"""
    # 啟動時執行
    market_hours = MarketTimeChecker.get_market_hours()
    scheduler.setup_tw_market_jobs(updater.get_stock_prices)
    scheduler.setup_us_market_jobs(updater.get_stock_prices, market_hours)
    scheduler.start()
    logger.info(f"應用程式啟動完成，當前時間: {get_current_time()}")

    yield

    # 關閉時執行
    scheduler.shutdown()
    logger.info("應用程式已關閉")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    """健康檢查端點"""
    current_time = get_current_time()
    return {
        "status": "running",
        "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "timezone": str(current_time.tzinfo),
    }


@app.get("/trigger")
async def trigger_update():
    """手動觸發更新的端點"""
    logger.info(f"手動觸發更新開始，當前時間: {get_current_time()}")
    data = updater.get_stock_prices(ignore_market_hours=True)  # 修改這裡
    return {"message": "更新完成", "data": data}


@app.get("/test_minute/{stock_id}")
async def test_minute_data(stock_id: str):
    """測試美股分鐘數據的端點

    Args:
        stock_id: 股票代碼，例如 "NVDA"

    Returns:
        JSON 格式的分鐘數據
    """
    logger.info(f"收到測試分鐘數據請求，股票代碼: {stock_id}")

    try:
        data = updater.api.get_us_stock_minute_price(stock_id)
        if not data:
            return {"status": "error", "message": "無法獲取數據"}

        return {
            "status": "success",
            "message": f"成功獲取 {stock_id} 的分鐘數據",
            "data": data,
        }

    except Exception as e:
        logger.error(f"處理請求時發生錯誤: {str(e)}")
        return {"status": "error", "message": f"處理請求時發生錯誤: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
