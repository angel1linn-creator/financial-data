# -*- coding: utf-8 -*-
"""
核心業務邏輯與分析模組 (analysis.py)
負責計算移轉定價 (TP) 財務比率指標、產業基準線 (Benchmark) 以及波動率 (Volatility)。
並提供便於 Streamlit 渲染與導出 CSV/Excel 的 Pivot Table 重構功能。
"""
import pandas as pd
import numpy as np
from models import get_db_session, FinancialData, Company

def calculate_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """
    計算核心移轉定價財務比率指標與衍生金額指標：
    - 毛利率 (gross_margin) = (營業毛利 / 營業收入) * 100
    - 營業利益率 (operating_margin) = (營業利益 / 營業收入) * 100
    - 稅後純益率 (net_margin) = (稅後純益 / 營業收入) * 100
    - 營業成本 (operating_cost) = 營業收入 - 營業毛利
    - 營業費用 (operating_expenses) = 營業毛利 - 營業利益
    
    參數:
        df (pd.DataFrame): 包含營業收入、營業毛利、營業利益、稅後純益的原始數據
    回傳:
        pd.DataFrame: 新增計算比例與衍生欄位後的 DataFrame
    """
    # 避免除以零的警告，如果營收為 0 則設為 NaN
    revenue = df["revenue"].replace(0, np.nan)
    
    # 比例指標 (%)
    df["gross_margin"] = (df["gross_profit"] / revenue) * 100
    df["operating_margin"] = (df["operating_income"] / revenue) * 100
    df["net_margin"] = (df["net_income"] / revenue) * 100
    
    # 金額指標 (由原始數據衍生)
    df["operating_cost"] = df["revenue"] - df["gross_profit"]
    df["operating_expenses"] = df["gross_profit"] - df["operating_income"]
    
    return df

def get_project_financial_df(project_id: int) -> pd.DataFrame:
    """
    從資料庫中撈取指定專案的所有公司財務數據，並計算比率指標。
    
    參數:
        project_id (int): 專案 ID
    回傳:
        pd.DataFrame: 整理後的 DataFrame
    """
    with get_db_session() as session:
        # 查詢該專案所有的財務明細
        records = session.query(FinancialData).filter(FinancialData.project_id == project_id).all()
        
        if not records:
            return pd.DataFrame()
            
        data = []
        for r in records:
            # 撈取對應的公司基本資訊以獲得公司名稱與產業標籤
            comp = session.query(Company).filter(Company.ticker == r.ticker).first()
            data.append({
                "ticker": r.ticker,
                "name": comp.name if comp else r.ticker,
                "industry_tag": comp.industry_tag if comp else "未分類",
                "year": r.year,
                "revenue": r.revenue,
                "gross_profit": r.gross_profit,
                "operating_income": r.operating_income,
                "net_income": r.net_income,
                "eps": r.eps,
                "is_tested_party": r.is_tested_party
            })
            
    df = pd.DataFrame(data)
    # 計算財務比率
    df = calculate_ratios(df)
    return df

def calculate_volatility(df: pd.DataFrame, metric: str) -> pd.Series:
    """
    計算指定財務指標在各公司五年期間的波動率（標準差）。
    
    參數:
        df (pd.DataFrame): 專案財務 DataFrame
        metric (str): 指標欄位名稱（如 "operating_margin"）
    回傳:
        pd.Series: 以 ticker 為 index 的標準差 series
    """
    if df.empty or metric not in df.columns:
        return pd.Series(dtype=float)
    return df.groupby("ticker")[metric].std()

def generate_pivot_table(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """
    重構 DataFrame 為樞紐分析表格式：
    - 橫軸為會計年度 (year)
    - 縱軸為公司名稱 (name) 或代號
    - 數值為指定財務指標 (metric)
    
    參數:
        df (pd.DataFrame): 專案財務 DataFrame
        metric (str): 財務比率或指標欄位（如 "gross_margin"、"operating_margin"、"net_margin"、"eps"）
    回傳:
        pd.DataFrame: 樞紐分析表
    """
    if df.empty or metric not in df.columns:
        return pd.DataFrame()
        
    # 以 ticker 與 name 作為 index，以 year 為 columns，以 metric 為 values
    pivot = df.pivot(index=["ticker", "name", "is_tested_party", "industry_tag"], columns="year", values=metric)
    # 重設索引，方便後續顯示或處理
    pivot = pivot.reset_index()
    return pivot

def get_industry_benchmarks(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """
    計算產業基準線 (Benchmark)。
    移轉定價實務中，基準線的計算會排除「受測企業 (Tested Party)」，
    僅計算同產業內其他可比公司 (Comparable Peers) 的算術平均值。
    
    參數:
        df (pd.DataFrame): 專案財務 DataFrame
        metric (str): 計算的財務指標
    回傳:
        pd.DataFrame: 包含產業各年度平均值的 DataFrame，例如：
                      columns: year, values: benchmark_value
    """
    if df.empty or metric not in df.columns:
        return pd.DataFrame()
        
    # 篩選非受測企業的可比同業
    peers_df = df[df["is_tested_party"] == False]
    
    if peers_df.empty:
        return pd.DataFrame()
        
    # 依據產業分類 (industry_tag) 與年度 (year) 計算指標的算術平均數
    benchmark = peers_df.groupby(["industry_tag", "year"])[metric].mean().reset_index()
    return benchmark
