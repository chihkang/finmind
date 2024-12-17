from typing import List, Dict, Optional
import pandas as pd
from core.market import MarketTimeChecker
from core.api import StockAPI
from config.constants import TPE_SUFFIX, TWO_SUFFIX
from utils.logger import get_logger

# 在所有需要使用時間的模組中
from utils.time_utils import get_current_time

logger = get_logger(__name__)


class StockPriceUpdater:
    def __init__(self):
        self.api = StockAPI()
        self.market_checker = MarketTimeChecker()

    def process_single_stock(self, stock: Dict) -> Optional[Dict]:
        """處理單一股票的價格更新"""
        stock_name = stock["name"]
        stock_id = stock_name.split(":")[0]
        is_us_stock = not any(
            stock_name.endswith(suffix) for suffix in (TPE_SUFFIX, TWO_SUFFIX)
        )

        try:
            # 根據市場類型獲取價格
            if is_us_stock:
                close_price = self.api.get_us_stock_price(stock_id)
            else:
                close_price = self.api.get_taiwan_stock_price(stock_id)

            if close_price is not None:
                logger.info(
                    f"準備更新股票 {stock_id} ({stock['alias']}) 的價格到 {close_price}"
                )
                update_success = self.api.update_stock_price(stock["_id"], close_price)
                update_status = "更新成功" if update_success else "更新失敗"
                logger.info(
                    f"{'[成功]' if update_success else '[失敗]'} {
                        update_status}：{stock_id} 價格 {close_price}"
                )

                current_time = get_current_time()
                return {
                    "股票代碼": stock_id,
                    "名稱": stock["alias"],
                    "市場": "US" if is_us_stock else "TW",
                    "日期": current_time.strftime("%Y-%m-%d"),
                    "收盤價": close_price,
                    "價格更新狀態": update_status,
                }
            else:
                logger.warning(f"沒有找到 {stock_id} 的資料")
                return None

        except Exception as e:
            logger.error(f"處理 {stock_id} 時發生錯誤: {e}")
            return None

    def get_stock_prices(
        self, ignore_market_hours: bool = False
    ) -> Optional[List[Dict]]:
        """獲取所有股票的最新價格並更新到 API

        Args:
            ignore_market_hours (bool): 是否忽略市場交易時間檢查，手動觸發時設為 True
        """
        self._log_task_start()

        stock_list = self._get_validated_stock_list()
        if not stock_list:
            return None

        all_stock_data = self._process_all_stocks(stock_list, ignore_market_hours)

        self._log_task_completion(all_stock_data)
        return all_stock_data

    def _log_task_start(self) -> None:
        """記錄任務開始時間"""
        current_time = get_current_time()
        logger.info(f"開始執行股票價格更新任務: {current_time}")

    def _get_validated_stock_list(self) -> Optional[List[Dict]]:
        """獲取並驗證股票列表"""
        stock_list = self.api.get_stock_list()
        if not stock_list:
            logger.warning("沒有找到符合條件的股票")
            return None
        return stock_list

    def _should_process_stock(self, stock: Dict, ignore_market_hours: bool) -> bool:
        """判斷是否應該處理該股票"""
        if ignore_market_hours:
            logger.info("手動觸發更新，忽略市場交易時間檢查")
            return True

        stock_name = stock["name"]
        is_us_stock = not any(
            stock_name.endswith(suffix) for suffix in (TPE_SUFFIX, TWO_SUFFIX)
        )

        return (is_us_stock and self.market_checker.is_us_market_hours()) or (
            not is_us_stock and self.market_checker.is_tw_market_hours()
        )

    def _process_all_stocks(
        self, stock_list: List[Dict], ignore_market_hours: bool
    ) -> List[Dict]:
        """處理所有股票數據"""
        all_stock_data = []

        for stock in stock_list:
            if self._should_process_stock(stock, ignore_market_hours):
                result = self.process_single_stock(stock)
                if result:
                    all_stock_data.append(result)

        return all_stock_data

    def _log_task_completion(self, all_stock_data: List[Dict]) -> None:
        """記錄任務完成情況"""
        self.display_results(all_stock_data)
        logger.info(f"任務完成時間: {get_current_time()}")

    @staticmethod
    @staticmethod
    def display_results(stock_data: List[Dict]):
        """顯示更新結果"""
        if not stock_data:
            logger.warning("沒有獲取到任何股票資料")
            return

        try:
            logger.info("\n股票最新報價:")
            logger.info("-" * 80)
            df_all = pd.DataFrame(stock_data)
            pd.set_option("display.float_format", lambda x: "%.2f" % x)
            pd.set_option("display.width", None)
            pd.set_option("display.max_rows", None)
            logger.info("\n" + df_all.to_string(index=False))
            logger.info("-" * 80)
        except Exception as e:
            logger.error(f"顯示結果時發生錯誤: {e}")
