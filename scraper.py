# -*- coding: utf-8 -*-
"""
數據抓取引擎 (scraper.py)
負責透過 yfinance 自動抓取台灣上市公司的財務數據，並進行標準化資料清洗。
"""
import pandas as pd
import yfinance as yf

# 產業類別英中對照表
INDUSTRY_MAP = {
    "Semiconductors": "半導體",
    "Computer Hardware": "電腦硬體/週邊",
    "Consumer Electronics": "消費性電子",
    "Electronic components": "電子零組件",
    "Electronic Components": "電子零組件",
    "Electronic Gaming & Multimedia": "遊戲與多媒體",
    "Internet Retail": "電子商務",
    "Software - Infrastructure": "基礎設施軟體",
    "Communication Services": "通訊服務",
    "Electronics & Computer Distribution": "電子通路",
    "Specialty Industrial Machinery": "工業機械",
    "Consumer Cyclical": "週期性消費",
    "Communication Services": "通訊服務",
    "Technology": "科技業"
}

def clean_ticker(ticker: str) -> str:
    """
    清理股票代號，確保符合 Yahoo Finance 格式。
    如果輸入為純數字（如 '2330'），則自動補上 '.TW' 後綴。
    """
    ticker = ticker.strip()
    if ticker.isdigit():
        return f"{ticker}.TW"
    return ticker

def fetch_financial_data(ticker_input: str, years: int = 5) -> dict:
    """
    抓取指定公司的財務數據、名稱與產業類別。
    """
    formatted_ticker = clean_ticker(ticker_input)
    print(f"[Scraper] 正在從 Yahoo Finance 抓取 {formatted_ticker} 的財務數據...")
    
    try:
        stock = yf.Ticker(formatted_ticker)
        
        # 1. 獲取公司基本資訊
        company_name = formatted_ticker.split(".")[0]
        industry_tag = "其他"
        try:
            info = stock.info
            if info and isinstance(info, dict):
                company_name = info.get("shortName", company_name)
                raw_industry = info.get("industry", info.get("sector", "其他"))
                # 進行英中翻譯轉換
                industry_tag = INDUSTRY_MAP.get(raw_industry, raw_industry)
                print(f"[Scraper] 偵測到產業: {raw_industry} -> {industry_tag}")
        except Exception as info_err:
            print(f"[Scraper] [警告] 無法取得 {formatted_ticker} 的基本資訊。原因: {info_err}")
        
        # 2. 獲取年度損益表 (Financials)
        df = stock.financials
        
        if df is None or df.empty:
            print(f"[Scraper] [錯誤] 找不到股票 {formatted_ticker} 的損益表數據。")
            return None
            
        # 3. 定義 Yahoo Finance 欄位對應
        target_mapping = {
            "Total Revenue": "revenue",
            "Gross Profit": "gross_profit",
            "Operating Income": "operating_income",
            "Net Income": "net_income"
        }
        eps_keys = ["Basic EPS", "Diluted EPS"]
        
        # 4. 提取各年度數據
        records = []
        for col_date in df.columns:
            year = col_date.year
            record = {
                "year": year,
                "revenue": 0.0,
                "gross_profit": 0.0,
                "operating_income": 0.0,
                "net_income": 0.0,
                "eps": None
            }
            
            has_valid_metric = False
            for yf_key, db_key in target_mapping.items():
                if yf_key in df.index:
                    val = df.loc[yf_key, col_date]
                    if pd.notna(val):
                        record[db_key] = float(val) / 1000.0
                        has_valid_metric = True
            
            for eps_key in eps_keys:
                if eps_key in df.index:
                    eps_val = df.loc[eps_key, col_date]
                    if pd.notna(eps_val):
                        record["eps"] = float(eps_val)
                        break
                        
            if has_valid_metric:
                records.append(record)
                
        records = sorted(records, key=lambda x: x["year"])
        records = records[-years:]
        
        result = {
            "ticker": formatted_ticker.split(".")[0],
            "name": company_name,
            "industry_tag": industry_tag,
            "records": records
        }
        
        print(f"[Scraper] 成功取得 {company_name} ({result['ticker']}) 產業: {industry_tag}")
        return result
        
    except Exception as e:
        print(f"[Scraper] [錯誤] 抓取 {formatted_ticker} 失敗，原因: {e}")
        return None

if __name__ == "__main__":
    print("啟動 Scraper 本地獨立功能驗證...")
    test_tickers = ["2330", "2357"]
    for t in test_tickers:
        res = fetch_financial_data(t, years=5)
        if res:
            print(f"公司: {res['name']} | 產業: {res['industry_tag']}")
        print("-" * 50)
