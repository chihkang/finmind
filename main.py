from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from core.scheduler import StockScheduler
from core.updater import StockPriceUpdater
from core.market import MarketTimeChecker
from config.settings import HOST, PORT
from utils.logger import get_logger

logger = get_logger(__name__)

# 初始化服務
updater = StockPriceUpdater()
scheduler = StockScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """處理應用程式的生命週期事件"""
    # 啟動時執行
    market_hours = MarketTimeChecker.get_market_hours()
    scheduler.setup_tw_market_jobs(updater.get_stock_prices)
    scheduler.setup_us_market_jobs(updater.get_stock_prices, market_hours)
    scheduler.start()
    logger.info("應用程式啟動完成")
    
    yield
    
    # 關閉時執行
    scheduler.shutdown()
    logger.info("應用程式已關閉")

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    """健康檢查端點"""
    return {"status": "running"}

@app.get("/trigger")
async def trigger_update():
    """手動觸發更新的端點"""
    data = updater.get_stock_prices()
    return {"message": "更新完成", "data": data}

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)