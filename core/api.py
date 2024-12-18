from typing import Optional, List, Dict
import requests
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime, timedelta
from config.constants import (
    FINMIND_API_URL,
    DATASETS,
    DATE_FORMAT,
    TWO_SUFFIX,
    TPE_SUFFIX,
)
from config.settings import API_BASE_URL, FINMIND_TOKEN
from utils.logger import get_logger
from utils.time_utils import get_current_time
from core.market import MarketTimeChecker
import pytz


logger = get_logger(__name__)


class StockAPI:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.finmind_token = FINMIND_TOKEN
        self.market_checker = MarketTimeChecker()
        self.api = self.initialize_api()  # 修正方法名稱，移除底線
        # 添加時區物件
        self.taipei_tz = pytz.timezone("Asia/Taipei")
        self.ny_tz = pytz.timezone("America/New_York")

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
        logger.info(f"開始獲取股票列表，請求網址: {url}")

        try:
            response = requests.get(url)
            logger.info(f"股票列表 API 回應狀態碼: {response.status_code}")

            response.raise_for_status()
            stocks = response.json()

            logger.info(f"獲取到原始股票資料數量: {len(stocks)}")

            # 分類股票
            tw_stocks = [
                s for s in stocks if s["name"].endswith((TPE_SUFFIX, TWO_SUFFIX))
            ]
            us_stocks = [
                s for s in stocks if not s["name"].endswith((TPE_SUFFIX, TWO_SUFFIX))
            ]

            # 記錄詳細統計資訊
            logger.info(f"找到台股共 {len(tw_stocks)} 支")
            logger.info(f"找到美股共 {len(us_stocks)} 支")

            if us_stocks:
                logger.info(
                    "美股代碼範例: " + ", ".join(s["name"] for s in us_stocks[:3])
                )

            all_stocks = tw_stocks + us_stocks
            logger.info(f"返回股票總數: {len(all_stocks)}")

            return all_stocks
        except requests.exceptions.RequestException as e:
            logger.error(f"獲取股票列表請求失敗: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"API 錯誤回應: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"獲取股票列表時發生未預期錯誤: {str(e)}")
            logger.exception("詳細錯誤資訊:")
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
                stock_id=stock_id, start_date=start_date, end_date=end_date
            )
            return df.iloc[-1]["close"] if not df.empty else None
        except Exception as e:
            logger.error(f"獲取台股 {stock_id} 價格失敗: {e}")
            return None

    def get_us_stock_price(self, stock_id: str) -> Optional[float]:
        """獲取美股最新價格"""
        clean_stock_id = stock_id.split(":")[0]
        logger.info(f"正在獲取美股 {clean_stock_id} 的價格...")

        current_time = get_current_time()
        logger.info(f"當前時間: {current_time}")

        trade_date = self._get_us_trade_date(current_time)
        is_trading_hours = self.market_checker.is_us_market_hours()

        if is_trading_hours:
            logger.info("當前為美股交易時段，使用分鐘數據...")
            dataset = DATASETS["US_MINUTE"]
            start_date = trade_date
            end_date = trade_date
        else:
            logger.info("當前為美股非交易時段，使用日線數據...")
            dataset = DATASETS["US_DAILY"]
            end_date = trade_date
            start_date = (
                datetime.strptime(trade_date, DATE_FORMAT) - timedelta(days=5)
            ).strftime(DATE_FORMAT)

        parameter = {
            "dataset": dataset,
            "data_id": clean_stock_id,
            "start_date": start_date,
            "end_date": end_date,
            "token": self.finmind_token,
        }

        logger.info(
            f"API 請求參數: dataset={dataset}, data_id={clean_stock_id}, "
            f"start_date={start_date}, end_date={end_date}"
        )

        try:
            response = requests.get(FINMIND_API_URL, params=parameter)
            logger.info(f"API 請求網址: {response.url}")
            logger.info(f"API 回應狀態碼: {response.status_code}")

            response.raise_for_status()
            data = response.json()

            if "data" not in data:
                logger.error(f"API 回應中沒有 data 欄位: {data}")
                return None

            df = pd.DataFrame(data["data"])
            if df.empty:
                logger.warning(
                    f"未找到 {clean_stock_id} 的價格數據，API 回應內容: {data}"
                )
                return None

            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date", ascending=False)
            logger.info(f"獲取到的數據範圍: {df['date'].min()} 到 {df['date'].max()}")

            price_column = "close" if is_trading_hours else "Close"
            latest_price = df.iloc[0][price_column]
            latest_date = df.iloc[0]["date"]

            logger.info(
                f"獲取到 {clean_stock_id} 在 {latest_date} 的收盤價: {latest_price}"
            )
            return latest_price

        except requests.exceptions.RequestException as e:
            logger.error(f"API 請求失敗: {str(e)}")
            if hasattr(e.response, "text"):
                logger.error(f"API 錯誤回應: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"獲取美股價格失敗: {str(e)}")
            logger.exception("詳細錯誤資訊:")
            return None

    def get_us_stock_minute_price(self, stock_id: str) -> Optional[dict]:
        """獲取美股分鐘數據，正確處理美股交易日期"""
        clean_stock_id = stock_id.split(":")[0]
        logger.info(f"開始獲取 {clean_stock_id} 的分鐘數據...")

        # 獲取當前台北時間
        taipei_time = get_current_time()
        logger.info(f"當前台北時間: {taipei_time}")

        # 將台北時間轉換為紐約時間
        taipei_tz = pytz.timezone("Asia/Taipei")
        ny_tz = pytz.timezone("America/New_York")
        taipei_time_aware = taipei_tz.localize(taipei_time.replace(tzinfo=None))
        ny_time = taipei_time_aware.astimezone(ny_tz)

        logger.info(f"對應的紐約時間: {ny_time}")

        # 如果紐約時間還在今天的美股盤前（以上午 9:30 為市場開盤時間參考）
        # 或者如果是紐約時間的周六周日，我們應該使用最近的一個交易日
        ny_date = ny_time.date()
        if ny_time.hour < 9 or (ny_time.hour == 9 and ny_time.minute < 30):
            ny_date = ny_date - timedelta(days=1)
            logger.info("紐約仍在盤前，使用前一個交易日")

        # 處理周末情況
        while ny_date.weekday() in [5, 6]:  # 5 是周六，6 是周日
            ny_date = ny_date - timedelta(days=1)
            logger.info("紐約時間為周末，往前調整至最近的工作日")

        trade_date = ny_date.strftime(DATE_FORMAT)
        logger.info(f"使用美股交易日期: {trade_date}")

        parameter = {
            "dataset": DATASETS["US_MINUTE"],
            "data_id": clean_stock_id,
            "start_date": trade_date,
            "end_date": trade_date,
            "token": self.finmind_token,
        }

        try:
            logger.info(
                f"發送請求參數: dataset={DATASETS['US_MINUTE']}, "
                f"data_id={clean_stock_id}, start_date={trade_date}, "
                f"end_date={trade_date}"
            )

            response = requests.get(FINMIND_API_URL, params=parameter)
            logger.info(f"API 請求 URL: {response.url}")
            logger.info(f"回應狀態碼: {response.status_code}")

            response.raise_for_status()
            data = response.json()

            if data.get("msg") != "success":
                logger.error(f"API 回應異常: {data}")
                return None

            if not data.get("data"):
                logger.warning(f"API 回應成功但無數據: {data}")
                return None

            # 記錄獲取到的數據時間範圍
            df = pd.DataFrame(data["data"])
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                time_range = f"從 {df['date'].min()} 到 {df['date'].max()}"
                logger.info(
                    f"成功獲取數據，時間範圍: {time_range}，資料筆數: {len(df)}"
                )
            else:
                logger.warning("獲取到的數據為空")

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"API 請求失敗: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"API 錯誤回應: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"處理數據時發生錯誤: {str(e)}")
            logger.exception("詳細錯誤信息:")
            return None

    def _get_us_trade_date(self, current_time=None) -> str:
        """計算美股交易日期

        Args:
            current_time: 可選，指定的時間點，預設使用當前時間

        Returns:
            str: 格式化的交易日期 (YYYY-MM-DD)
        """
        if current_time is None:
            current_time = get_current_time()

        # 轉換為紐約時間
        taipei_tz = pytz.timezone("Asia/Taipei")
        ny_tz = pytz.timezone("America/New_York")
        taipei_time_aware = taipei_tz.localize(current_time.replace(tzinfo=None))
        ny_time = taipei_time_aware.astimezone(ny_tz)

        logger.info(f"台北時間: {current_time}, 紐約時間: {ny_time}")

        # 計算交易日期
        ny_date = ny_time.date()
        if ny_time.hour < 9 or (ny_time.hour == 9 and ny_time.minute < 30):
            ny_date = ny_date - timedelta(days=1)
            logger.info("紐約仍在盤前，使用前一個交易日")

        # 處理周末情況
        while ny_date.weekday() in [5, 6]:
            ny_date = ny_date - timedelta(days=1)
            logger.info("紐約時間為周末，往前調整至最近的工作日")

        return ny_date.strftime(DATE_FORMAT)
