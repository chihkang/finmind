from apscheduler.schedulers.background import BackgroundScheduler
from config.constants import (
    SCHEDULER_TIMEZONE,
    UPDATE_INTERVAL
)
from utils.logger import get_logger

logger = get_logger(__name__)

class StockScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        
    def setup_tw_market_jobs(self, job_function):
        """設置台股市場的排程工作"""
        # 台股交易時段 (9:00-13:35)
        self.scheduler.add_job(
            job_function,
            'cron',
            day_of_week='mon-fri',
            hour='9-13',
            minute=UPDATE_INTERVAL,
            timezone=SCHEDULER_TIMEZONE,
            id='tw_market_job'
        )
        
        # 台股收盤時段
        self.scheduler.add_job(
            job_function,
            'cron',
            day_of_week='mon-fri',
            hour='13',
            minute='30-35/5',
            timezone=SCHEDULER_TIMEZONE,
            id='tw_market_closing_job'
        )
        logger.info("已設置台股市場排程工作")

    def setup_us_market_jobs(self, job_function, market_hours):
        """設置美股市場的排程工作"""
        start_time, end_time = market_hours
        start_hour = int(start_time.split(':')[0])
        start_minute = int(start_time.split(':')[1])
        end_hour = int(end_time.split(':')[0])
        
        # 美股晚間排程
        if start_hour >= 21:
            self.scheduler.add_job(
                job_function,
                'cron',
                day_of_week='mon-fri',
                hour=f'{start_hour}-23',
                minute=f'{start_minute}/5',
                timezone=SCHEDULER_TIMEZONE,
                id='us_market_evening_job'
            )
        
        # 美股凌晨排程
        if end_hour <= 5:
            self.scheduler.add_job(
                job_function,
                'cron',
                day_of_week='tue-sat',  # 因為跨日，所以要用 tue-sat
                hour=f'0-{end_hour}',
                minute=UPDATE_INTERVAL,
                timezone=SCHEDULER_TIMEZONE,
                id='us_market_morning_job'
            )
        logger.info("已設置美股市場排程工作")

    def start(self):
        """啟動排程器"""
        self.scheduler.start()
        logger.info("排程器已啟動")

    def shutdown(self):
        """關閉排程器"""
        self.scheduler.shutdown()
        logger.info("排程器已關閉")