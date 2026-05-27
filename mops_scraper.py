# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf


def get_yf_income_statement(ticker="2330.TW"):
    print("==================================================")
    print(f" 🚀 正在透過 yfinance 請求 Yahoo Finance 數據...")
    print(f" 📊 目標股票代號 -> {ticker}")
    print("==================================================")

    try:
        # 1. 建立 Ticker 物件
        stock = yf.Ticker(ticker)

        # 2. 獲取年度綜合損益表 (Financials)
        # yfinance 回傳的 DataFrame 欄位是西元日期 (例如 2023-12-31)，列索引是英文會計科目
        df = stock.financials

        if df.empty:
            print("❌ 錯誤：找不到該股票的財報數據，請檢查代號是否正確。")
            return None

        # 3. 定義 Yahoo Finance 對應的英文會計科目
        # 為了對應您原本需求的四個欄位：營業收入、營業毛利、營業利益、本期淨利
        target_mapping = {
            "Total Revenue": "營業收入",
            "Gross Profit": "營業毛利",
            "Operating Income": "營業利益",
            "Net Income": "本期淨利",
        }

        print("\n🏆 【提取財報數據結果】(最新四個年度)")
        print("-" * 50)

        # 4. 依序提取指定的欄位
        for eng_name, ch_name in target_mapping.items():
            if eng_name in df.index:
                # 取得該項目整行的數據 (包含好幾個年度)
                row_data = df.loc[eng_name]

                print(f"📌 {ch_name} ({eng_name}):")
                # 遍歷每個年度印出數據
                for date, val in row_data.items():
                    # 格式化日期只顯示年份
                    year_str = str(date)[:4]
                    # 如果數值不是 NaN，進行千分位格式化呈現
                    if pd.notna(val):
                        print(f"  📅 {year_str} 年: {val:,.0f}")
                    else:
                        print(f"  📅 {year_str} 年: 無資料")
            else:
                print(f"❌ 在 Yahoo Finance 中找不到對應欄位: {ch_name}")

        print("==================================================")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")


if __name__ == "__main__":
    # 台股請務必記得加上 .TW 後綴
    get_yf_income_statement(ticker="2330.TW")
    input("\n請按 Enter 鍵結束程式...")
