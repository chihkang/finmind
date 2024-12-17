from typing import Optional, List, Dict
import requests
import pandas as pd
from FinMind.data import DataLoader
from datetime import timedelta
from config.constants import (
    FINMIND_API_URL, DATASETS, DATE_FORMAT,
    TWO_SUFFIX, TPE_SUFFIX
)
from config.settings import API_BASE_URL, FINMIND_TOKEN
from utils.logger import get_logger
from utils.time_utils import get_current_time
from core.market import MarketTimeChecker

logger = get_logger(__name__)


class StockAPI:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.finmind_token = FINMIND_TOKEN
        self.market_checker = MarketTimeChecker()
        self.api = self.initialize_api()  # 修正方法名稱，移除底線

    def initialize_api(self) -> Optional[DataLoader]:
        """初始化 FinMind API"""
        if not self.finmind_token:
            logger.error("找不到 FINMIND_TOKEN 環境變數")
            return None

        api = DataLoader()
        try:
            api.login_by_token(api_token=self.finmind_token)
            logger.info("FinMind API Token 登入成功")
            return api
        except Exception as e:
            logger.error(f"FinMind API 登入失敗: {e}")
            return None

    def get_stock_list(self) -> List[Dict]:
        """從API獲取股票列表"""
        url = f"{self.base_url}/api/stocks/minimal"
        try:
            response = requests.get(url)
            response.raise_for_status()
            stocks = response.json()

            # 分類股票
            tw_stocks = [s for s in stocks if s['name'].endswith(
                (TPE_SUFFIX, TWO_SUFFIX))]
            us_stocks = [s for s in stocks if not s['name'].endswith(
                (TPE_SUFFIX, TWO_SUFFIX))]

            # 記錄統計資訊
            logger.info(f"找到台股共 {len(tw_stocks)} 支")
            logger.info(f"找到美股共 {len(us_stocks)} 支")

            return tw_stocks + us_stocks
        except Exception as e:
            logger.error(f"獲取股票列表失敗: {e}")
            return []

    def update_stock_price(self, stock_id: str, price: float) -> bool:
        """更新股票價格到 API"""
        url = f"{self.base_url}/api/stocks/id/{stock_id}/price"
        headers = {"Accept": "application/json"}
        params = {"newPrice": price}

        try:
            response = requests.put(url, headers=headers, params=params)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"更新股票價格失敗: {e}")
            return False

    def get_taiwan_stock_price(self, stock_id: str) -> Optional[float]:
        """獲取台股價格"""
        if not self.api:
            return None

        current_time = get_current_time()
        end_date = current_time.strftime(DATE_FORMAT)
        start_date = (current_time - timedelta(days=5)).strftime(DATE_FORMAT)

        try:
            df = self.api.taiwan_stock_daily(
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date
            )
            return df.iloc[-1]['close'] if not df.empty else None
        except Exception as e:
            logger.error(f"獲取台股 {stock_id} 價格失敗: {e}")
            return None

    def get_us_stock_price(self, stock_id: str) -> Optional[float]:
        """獲取美股最新價格"""
        clean_stock_id = stock_id.split(':')[0]
        logger.info(f"正在獲取美股 {clean_stock_id} 的價格...")

        current_time = get_current_time()

        is_trading_hours = self.market_checker.is_us_market_hours()
        if is_trading_hours:
            logger.info("當前為美股交易時段，使用分鐘數據...")
            dataset = DATASETS['US_MINUTE']
            start_date = current_time.strftime(DATE_FORMAT)
            end_date = start_date
        else:
            logger.info("當前為美股非交易時段，使用日線數據...")
            dataset = DATASETS['US_DAILY']
            end_date = current_time.strftime(DATE_FORMAT)
            start_date = (current_time - timedelta(days=5)).strftime(DATE_FORMAT)

        parameter = {
            "dataset": dataset,
            "data_id": clean_stock_id,
            "start_date": start_date,
            "end_date": end_date,
            "token": self.finmind_token,
        }

        try:
            response = requests.get(FINMIND_API_URL, params=parameter)
            response.raise_for_status()
            data = response.json()

            if 'data' not in data:
                logger.error(f"API 回應中沒有 data 欄位: {data}")
                return None

            df = pd.DataFrame(data['data'])
            if df.empty:
                logger.warning(f"未找到 {clean_stock_id} 的價格數據")
                return None

            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)

            # 取得最新的收盤價，注意分鐘數據和日線數據的 column name 不同
            price_column = 'close' if is_trading_hours else 'Close'
            latest_price = df.iloc[0][price_column]
            latest_date = df.iloc[0]['date']

            logger.info(f"獲取到 {clean_stock_id} 在 {latest_date} 的收盤價: {latest_price}")
            return latest_price

        except Exception as e:
            logger.error(f"獲取美股價格失敗: {e}")
            return None
