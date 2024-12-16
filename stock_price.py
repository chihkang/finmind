from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os
import requests
from FinMind.data import DataLoader
from datetime import datetime, timedelta
import pandas as pd
import uvicorn

# 載入 .env 文件
load_dotenv()

scheduler = BackgroundScheduler()

def is_dst():
    """
    判斷現在是否為夏令時間
    美國夏令時間：3月第二個週日 - 11月第一個週日
    """
    now = datetime.now()
    year = now.year
    
    # 計算3月第二個週日
    march = datetime(year, 3, 1)
    march_second_sunday = march + timedelta(days=(13 - march.weekday()))
    
    # 計算11月第一個週日
    november = datetime(year, 11, 1)
    november_first_sunday = november + timedelta(days=(6 - november.weekday()))
    
    return march_second_sunday <= now < november_first_sunday

def get_us_market_hours():
    """
    根據夏令/冬令時間獲取美股交易時間
    """
    if is_dst():
        start_time = os.getenv('US_MARKET_SUMMER_START', '21:30')
        end_time = os.getenv('US_MARKET_SUMMER_END', '04:00')
    else:
        start_time = os.getenv('US_MARKET_WINTER_START', '22:30')
        end_time = os.getenv('US_MARKET_WINTER_END', '05:00')
    
    return start_time, end_time

def get_stock_list():
    """
    從API獲取股票列表，返回台股和美股
    """
    base_url = os.getenv('API_BASE_URL')
    url = f"{base_url}/api/stocks/minimal"
    try:
        response = requests.get(url)
        response.raise_for_status()
        stocks = response.json()
        
        # 分別統計台股和美股數量
        tw_stocks = [stock for stock in stocks if stock['name'].endswith((':TPE', ':TWO'))]
        us_stocks = [stock for stock in stocks if not stock['name'].endswith((':TPE', ':TWO'))]
        
        # 輸出統計資訊
        print(f"\n找到 TPE 和 TWO 股票共 {len(tw_stocks)} 支")
        print(f"TPE 股票: {len([s for s in tw_stocks if s['name'].endswith(':TPE')])} 支")
        print(f"TWO 股票: {len([s for s in tw_stocks if s['name'].endswith(':TWO')])} 支")
        print(f"美股: {len(us_stocks)} 支")
        
        # 返回所有股票（台股 + 美股）
        return tw_stocks + us_stocks
        
    except Exception as e:
        print(f"獲取股票列表時發生錯誤: {e}")
        return []

def update_stock_price(stock_id: str, price: float) -> bool:
    """更新股票價格到 API"""
    base_url = os.getenv('API_BASE_URL')
    url = f"{base_url}/api/stocks/id/{stock_id}/price"
    headers = {"Accept": "application/json"}
    params = {"newPrice": price}
    
    try:
        response = requests.put(url, headers=headers, params=params)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"更新價格時發生錯誤: {e}")
        return False

def is_us_market_hours() -> bool:
    """
    判斷當前是否為美股交易時段（台北時間）
    """
    now = datetime.now()
    current_time = now.time()
    
    # 獲取當前是否為夏令時間
    is_summer = is_dst()
    
    if is_summer:
        # 夏令時間：台北時間 21:30-04:00
        start_time = datetime.strptime("21:30", "%H:%M").time()
        end_time = datetime.strptime("04:00", "%H:%M").time()
    else:
        # 冬令時間：台北時間 22:30-05:00
        start_time = datetime.strptime("22:30", "%H:%M").time()
        end_time = datetime.strptime("05:00", "%H:%M").time()
    
    # 跨午夜的情況需要特別處理
    if start_time > end_time:
        return current_time >= start_time or current_time <= end_time
    return start_time <= current_time <= end_time

def get_last_us_trading_date() -> str:
    """
    獲取上一個美股交易日的日期
    """
    now = datetime.now()
    
    # 如果是週一，回傳上週五的日期
    if now.weekday() == 0:
        last_trading_date = now - timedelta(days=3)
    # 如果是週日，回傳上週五的日期
    elif now.weekday() == 6:
        last_trading_date = now - timedelta(days=2)
    # 其他情況回傳前一天
    else:
        last_trading_date = now - timedelta(days=1)
    
    return last_trading_date.strftime("%Y-%m-%d")

def get_us_stock_price(api: DataLoader, stock_id: str) -> float:
    """獲取美股最新價格"""
    url = 'https://api.finmindtrade.com/api/v4/data'
    token = os.getenv('FINMIND_TOKEN')
    
    # 移除 :NASDAQ 等後綴
    clean_stock_id = stock_id.split(':')[0]
    print(f"\n正在獲取美股 {clean_stock_id} 的價格...")
    
    # 判斷是否為美股交易時段
    is_trading_hours = is_us_market_hours()
    
    if is_trading_hours:
        print("當前為美股交易時段，使用分鐘數據...")
        dataset = "USStockPriceMinute"
        # 使用當天數據
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = start_date
    else:
        print("當前為美股非交易時段，使用日線數據...")
        dataset = "USStockPrice"
        # 使用上一個交易日數據
        end_date = get_last_us_trading_date()
        start_date = end_date
    
    parameter = {
        "dataset": dataset,
        "data_id": clean_stock_id,
        "start_date": start_date,
        "end_date": end_date,
        "token": token,
    }
    
    try:
        print(f"發送請求到 FinMind API, 參數: {parameter}")
        response = requests.get(url, params=parameter)
        response.raise_for_status()
        data = response.json()
        
        if 'data' not in data:
            print(f"API 回應中沒有 data 欄位: {data}")
            return None
            
        df = pd.DataFrame(data['data'])
        
        if df.empty:
            print(f"未找到 {clean_stock_id} 的價格數據")
            return None
        
        # 排序確保獲取最新數據
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date', ascending=False)
        
        # 輸出最後幾筆數據以供檢查
        print(f"\n{clean_stock_id} 最後幾筆價格數據 (來自 {dataset}):")
        print(df.head().to_string())
        
        latest_price = df.iloc[0]['Close']
        print(f"獲取到 {clean_stock_id} 的最新價格: {latest_price}")
        return latest_price
        
    except requests.exceptions.RequestException as e:
        print(f"API 請求錯誤: {e}")
        print(f"回應內容: {e.response.text if hasattr(e, 'response') else '無回應內容'}")
        return None
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")
        return None

def get_stock_prices():
    """獲取所有股票的最新價格並更新到 API"""
    print(f"開始執行股票價格更新任務: {datetime.now()}")
    
    api_token = os.getenv('FINMIND_TOKEN')
    if not api_token:
        print("錯誤：找不到 FINMIND_TOKEN 環境變數")
        return

    api = DataLoader()
    try:
        api.login_by_token(api_token=api_token)
        print("Token 登入成功！")
    except Exception as e:
        print(f"登入失敗: {e}")
        return
    
    stock_list = get_stock_list()
    if not stock_list:
        print("沒有找到符合條件的股票")
        return
    
    all_stock_data = []
    
    for stock in stock_list:
        stock_name = stock['name']
        stock_id = stock_name.split(':')[0]
        
        # 判斷是台股還是美股
        is_us_stock = not any(stock_name.endswith(suffix) for suffix in (':TPE', ':TWO'))
        
        try:
            if is_us_stock:
                # 處理美股
                close_price = get_us_stock_price(api, stock_id)
            else:
                # 處理台股
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
                
                df = api.taiwan_stock_daily(
                    stock_id=stock_id,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if not df.empty:
                    close_price = df.iloc[-1]['close']
                else:
                    close_price = None
            
            if close_price is not None:
                print(f"\n準備更新股票 {stock_id} ({stock['alias']}) 的價格到 {close_price}")
                if update_stock_price(stock['_id'], close_price):
                    print(f"✓ 成功更新股票 {stock_id} 的價格到 {close_price}")
                    update_status = '更新成功'
                else:
                    print(f"✗ 更新股票 {stock_id} 的價格失敗")
                    update_status = '更新失敗'
                
                stock_data = {
                    '股票代碼': stock_id,
                    '名稱': stock['alias'],
                    '市場': 'US' if is_us_stock else 'TW',
                    '日期': datetime.now().strftime("%Y-%m-%d"),
                    '收盤價': close_price,
                    '價格更新狀態': update_status
                }
                all_stock_data.append(stock_data)
            else:
                print(f"沒有找到 {stock_id} 的資料")
                
        except Exception as e:
            print(f"處理 {stock_id} 時發生錯誤: {e}")
            continue
    
    if all_stock_data:
        print("\n股票最新報價:")
        print("-" * 80)
        df_all = pd.DataFrame(all_stock_data)
        pd.set_option('display.float_format', lambda x: '%.2f' % x)
        pd.set_option('display.width', None)
        pd.set_option('display.max_rows', None)
        print(df_all.to_string(index=False))
        print("-" * 80)
    else:
        print("沒有獲取到任何股票資料")
    
    print(f"任務完成時間: {datetime.now()}")
    return all_stock_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    """處理應用程式的生命週期事件"""
    # 啟動時執行
    init_scheduler()
    yield
    # 關閉時執行
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

def init_scheduler():
    """初始化排程器"""
    # 台股排程 (台北時間 9:00-13:35)
    scheduler.add_job(
        get_stock_prices,
        'cron',
        day_of_week='mon-fri',
        hour='9-13',
        minute='*/5',
        end_date=None,
        timezone='Asia/Taipei'
    )
    
    scheduler.add_job(
        get_stock_prices,
        'cron',
        day_of_week='mon-fri',
        hour='13',
        minute='30-35/5',
        end_date=None,
        timezone='Asia/Taipei'
    )
    
    # 獲取美股交易時間
    us_start, us_end = get_us_market_hours()
    start_hour = int(us_start.split(':')[0])
    start_minute = int(us_start.split(':')[1])
    end_hour = int(us_end.split(':')[0])
    
    # 美股晚間排程
    if start_hour >= 21:
        scheduler.add_job(
            get_stock_prices,
            'cron',
            day_of_week='mon-fri',
            hour=f'{start_hour}-23',
            minute=f'{start_minute}/5',
            end_date=None,
            timezone='Asia/Taipei'
        )
    
    # 美股凌晨排程
    if end_hour <= 5:
        scheduler.add_job(
            get_stock_prices,
            'cron',
            day_of_week='tue-sat',  # 因為跨日，所以要用 tue-sat
            hour=f'0-{end_hour}',
            minute='*/5',
            end_date=None,
            timezone='Asia/Taipei'
        )
    
    scheduler.start()

@app.get("/")
async def root():
    """健康檢查端點"""
    return {"status": "running"}

@app.get("/trigger")
async def trigger_update():
    """手動觸發更新的端點"""
    data = get_stock_prices()
    return {"message": "更新完成", "data": data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))