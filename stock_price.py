from dotenv import load_dotenv
import os
import requests
from FinMind.data import DataLoader
from datetime import datetime, timedelta
import pandas as pd

# 載入 .env 文件
load_dotenv()

def get_stock_list():
    """
    從API獲取股票列表，並篩選出TPE結尾的股票
    """
    url = "http://minimalapi-chiseled-production.up.railway.app/api/stocks/minimal"
    try:
        response = requests.get(url)
        response.raise_for_status()
        stocks = response.json()
        
        # 篩選出name末三碼為TPE的股票
        tpe_stocks = [stock for stock in stocks if stock['name'].endswith(':TPE')]
        return tpe_stocks
    except Exception as e:
        print(f"獲取股票列表時發生錯誤: {e}")
        return []

def get_stock_prices():
    """
    獲取所有TPE股票的最新價格
    """
    # 從環境變數獲取 Token
    api_token = os.getenv('FINMIND_TOKEN')
    if not api_token:
        print("錯誤：找不到 FINMIND_TOKEN 環境變數")
        return

    # 初始化 DataLoader 並登入
    api = DataLoader()
    try:
        api.login_by_token(api_token=api_token)
        print("Token 登入成功！")
    except Exception as e:
        print(f"登入失敗: {e}")
        return
    
    # 獲取股票列表
    stock_list = get_stock_list()
    if not stock_list:
        print("沒有找到符合條件的股票")
        return
    
    print(f"\n找到 {len(stock_list)} 支TPE股票")
    print("-" * 80)
    
    # 設定日期範圍
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    
    # 儲存所有股票的最新資料
    all_stock_data = []
    
    for stock in stock_list:
        # 從name欄位中提取股票代碼（去除:TPE部分）
        stock_id = stock['name'].split(':')[0]
        try:
            # 獲取股票數據
            df = api.taiwan_stock_daily(
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if not df.empty:
                # 獲取最新一筆資料
                latest_data = df.iloc[-1]
                stock_data = {
                    '股票代碼': stock_id,
                    '名稱': stock['alias'],
                    '日期': latest_data['date'],
                    '收盤價': latest_data['close']
                }
                all_stock_data.append(stock_data)
                print(f"處理中: {stock_id} ({stock['alias']})")
            else:
                print(f"沒有找到 {stock_id} 的資料")
                
        except Exception as e:
            print(f"獲取 {stock_id} 數據時發生錯誤: {e}")
            continue
    
    # 將所有資料轉換為DataFrame並顯示
    if all_stock_data:
        print("\n股票最新報價:")
        print("-" * 80)
        df_all = pd.DataFrame(all_stock_data)
        # 設定顯示選項，確保數字格式正確
        pd.set_option('display.float_format', lambda x: '%.2f' % x)
        pd.set_option('display.width', None)
        pd.set_option('display.max_rows', None)
        print(df_all.to_string(index=False))
        print("-" * 80)
    else:
        print("沒有獲取到任何股票資料")

if __name__ == "__main__":
    get_stock_prices()