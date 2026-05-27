# -*- coding: utf-8 -*-
"""
Streamlit Web 使用者介面主程式 (app.py)
整合數據抓取引擎與財務分析邏輯，提供財務/稅務經理一站式移轉定價 (TP) 輔助分析與視覺化儀表板。
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import yfinance as yf

# 導入自訂模組
from models import init_db, get_db_session, Project, Company, FinancialData
from scraper import clean_ticker, fetch_financial_data
from analysis import (
    get_project_financial_df, 
    generate_pivot_table, 
    get_industry_benchmarks, 
    calculate_volatility
)

# 1. 頁面基本配置
st.set_page_config(
    page_title="TP Analytics - 移轉定價自動化分析系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自訂 CSS 樣式
st.markdown("""
<style>
    .main { background-color: #fcfdfe; }
    .stApp { background-color: #fcfdfe; }
    .top-gradient-bar {
        height: 6px;
        background: linear-gradient(90deg, #2c3e50 0%, #3498db 50%, #2ecc71 100%);
        width: 100%; position: fixed; top: 0; left: 0; z-index: 1000;
    }
    .main-title { color: #2c3e50; font-weight: 800; font-size: 2.4rem; margin-top: 1rem; }
    .subtitle { color: #7f8c8d; font-size: 1.1rem; margin-bottom: 2rem; }
    .metric-card {
        background-color: white; padding: 18px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #eef2f6;
        margin-bottom: 15px;
    }
    .metric-label { font-size: 0.75rem; text-transform: uppercase; color: #7f8c8d; font-weight: 600; }
    .metric-val { font-size: 1.8rem; font-weight: 700; color: #2c3e50; margin-top: 5px; }
    .tip-box {
        background-color: #f7f9fa; border-left: 4px solid #3498db;
        padding: 12px 15px; border-radius: 0 8px 8px 0; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-gradient-bar"></div>', unsafe_allow_html=True)

# 初始化資料庫
init_db()

# --- 輔助函數：獲取股價資訊 ---
def get_stock_price_info(ticker):
    from scraper import clean_ticker
    yf_ticker = clean_ticker(ticker)
    try:
        stock = yf.Ticker(yf_ticker)
        current_price = stock.fast_info.get("lastPrice", 0.0)
        hist = stock.history(period="5y")
        if not hist.empty:
            total_avg = hist["Close"].mean()
            hist['Year'] = hist.index.year
            yearly_avg_dict = hist.groupby('Year')['Close'].mean().to_dict()
        else:
            total_avg = 0.0
            yearly_avg_dict = {}
        return current_price, total_avg, yearly_avg_dict
    except:
        return 0.0, 0.0, {}

# --- 側邊欄與導航 ---
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "專案與公司管理"

st.sidebar.markdown("### 📊 移轉定價分析工作空間")

# 獲取所有專案列表
with get_db_session() as session:
    projects = session.query(Project).order_by(Project.created_at.desc()).all()
    project_options = {p.id: p.name for p in projects}

# 建立新專案
st.sidebar.markdown("---")
st.sidebar.markdown("#### 📂 建立新專案")
new_project_name = st.sidebar.text_input("專案名稱", placeholder="例如：2026年度 TP 分析", key="new_proj_name")
if st.sidebar.button("➕ 建立專案", use_container_width=True):
    if new_project_name.strip():
        with get_db_session() as session:
            existing = session.query(Project).filter(Project.name == new_project_name.strip()).first()
            if not existing:
                session.add(Project(name=new_project_name.strip()))
                session.commit()
                st.sidebar.success("✅ 建立成功！")
                st.rerun()
            else:
                st.sidebar.error("⚠️ 名稱已存在")

if project_options:
    st.sidebar.markdown("---")
    selected_project_id = st.sidebar.selectbox("📁 選擇目前專案", options=list(project_options.keys()), format_func=lambda x: project_options[x])
else:
    selected_project_id = None

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🧭 功能導覽")
if st.sidebar.button("🏢 專案與公司管理", use_container_width=True):
    st.session_state["active_tab"] = "專案與公司管理"
    st.rerun()
if st.sidebar.button("📈 移轉定價儀表板", use_container_width=True):
    st.session_state["active_tab"] = "移轉定價儀表板"
    st.rerun()
if st.sidebar.button("🎯 公司深度分析", use_container_width=True):
    st.session_state["active_tab"] = "公司深度分析"
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("#### ⚙️ 系統管理")
if st.sidebar.button("🔄 同步所有產業類別", use_container_width=True):
    with st.spinner("正在同步產業類別..."):
        from sync_industries import sync_industries
        try:
            sync_industries()
            st.sidebar.success("✅ 產業類別同步完成！")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"❌ 同步失敗: {e}")

# --- 分頁內容渲染 ---
if st.session_state["active_tab"] == "專案與公司管理":
    st.markdown('<h1 class="main-title">🏢 專案與公司管理</h1>', unsafe_allow_html=True)
    if not selected_project_id:
        st.info("👋 請先選取或建立專案。")
    else:
        df_current = get_project_financial_df(selected_project_id)
        if not df_current.empty:
            st.markdown("#### 📋 已加入公司清單")
            comp_list = df_current.groupby(["ticker", "name", "industry_tag", "is_tested_party"]).size().reset_index()
            comp_list.columns = ["股票代號", "公司名稱", "產業標籤", "受測企業", "資料筆數"]
            st.dataframe(comp_list.style.format({"受測企業": lambda x: "🔥 受測企業" if x else "⚖️ 可比同業"}), use_container_width=True, hide_index=True)
            
            # 設定 Tested Party
            col_tp_1, col_tp_2 = st.columns([3, 1])
            with col_tp_1:
                selected_tp = st.selectbox("🎯 指定「受測企業」", options=comp_list["股票代號"].tolist())
            with col_tp_2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("💾 確認設定", use_container_width=True):
                    with get_db_session() as session:
                        session.query(FinancialData).filter(FinancialData.project_id == selected_project_id).update({FinancialData.is_tested_party: False})
                        session.query(FinancialData).filter(FinancialData.project_id == selected_project_id, FinancialData.ticker == selected_tp).update({FinancialData.is_tested_party: True})
                        session.commit()
                        st.rerun()

        st.markdown("---")
        st.markdown("### 📥 自動化數據抓取")
        tickers_input = st.text_input("輸入股票代號（逗號分隔）", placeholder="2330, 2382")
        if st.button("🚀 開始自動抓取", use_container_width=True):
            if tickers_input.strip():
                raw_tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]
                my_bar = st.progress(0)
                for idx, t_raw in enumerate(raw_tickers):
                    my_bar.progress(int((idx/len(raw_tickers))*100))
                    res = fetch_financial_data(t_raw)
                    if res:
                        with get_db_session() as session:
                            comp = session.query(Company).filter(Company.ticker == res["ticker"]).first()
                            if not comp:
                                session.add(Company(ticker=res["ticker"], name=res["name"], industry_tag=res["industry_tag"]))
                            else:
                                # 更新現有公司的產業標籤與名稱
                                comp.name = res["name"]
                                comp.industry_tag = res["industry_tag"]
                            
                            session.query(FinancialData).filter(FinancialData.project_id == selected_project_id, FinancialData.ticker == res["ticker"]).delete()
                            for rec in res["records"]:
                                session.add(FinancialData(project_id=selected_project_id, ticker=res["ticker"], year=rec["year"], revenue=rec["revenue"], gross_profit=rec["gross_profit"], operating_income=rec["operating_income"], net_income=rec["net_income"], eps=rec["eps"]))
                            session.commit()
                st.rerun()

        # 移除專案中的公司區塊 (樣式與抓取一致)
        st.markdown("---")
        st.markdown("### 🗑️ 移除專案中的公司")
        st.warning("注意：移除後將刪除該公司在此專案中的所有財務數據。")
        delete_options = comp_list["股票代號"].tolist() if not df_current.empty else []
        to_delete = st.multiselect("選擇要移除的公司", options=delete_options)
        if st.button("🔥 確認移除選取公司", type="primary", use_container_width=True):
            if to_delete:
                with get_db_session() as session:
                    session.query(FinancialData).filter(
                        FinancialData.project_id == selected_project_id, 
                        FinancialData.ticker.in_(to_delete)
                    ).delete(synchronize_session=False)
                    session.commit()
                    st.success(f"✅ 已成功移除 {len(to_delete)} 家公司")
                    st.rerun()
            else:
                st.error("請先選擇要移除的公司。")

elif st.session_state["active_tab"] == "移轉定價儀表板":

    st.markdown('<h1 class="main-title">📈 移轉定價儀表板</h1>', unsafe_allow_html=True)
    if not selected_project_id:
        st.info("👋 請先選取專案。")
    else:
        df_proj = get_project_financial_df(selected_project_id)
        if df_proj.empty:
            st.warning("⚠️ 目前專案尚無數據。")
        else:
            metric_option = st.radio(
                "選擇指標：", 
                options=[
                    "營業利益率 (Operating Margin)", 
                    "毛利率 (Gross Margin)", 
                    "稅後純益率 (Net Margin)", 
                    "每股盈餘 (EPS)",
                    "營業收入 (Revenue)",
                    "營業成本 (COGS)",
                    "營業費用 (OpEx)"
                ], 
                horizontal=True
            )
            metric_mapping = {
                "營業利益率 (Operating Margin)": "operating_margin", 
                "毛利率 (Gross Margin)": "gross_margin", 
                "稅後純益率 (Net Margin)": "net_margin", 
                "每股盈餘 (EPS)": "eps",
                "營業收入 (Revenue)": "revenue",
                "營業成本 (COGS)": "operating_cost",
                "營業費用 (OpEx)": "operating_expenses"
            }
            db_metric = metric_mapping[metric_option]
            
            # 判斷單位與數值縮放
            is_percentage = db_metric.endswith("_margin")
            is_money_m = db_metric in ["revenue", "operating_cost", "operating_expenses"]
            
            unit_str = "%" if is_percentage else "千元"
            if is_money_m: unit_str = "百萬元"
            if db_metric == "eps": unit_str = "元"
            
            # 獲取 Pivot Table 並處理金額縮放 (千元 -> 百萬元)
            df_pivot = generate_pivot_table(df_proj, db_metric)
            if is_money_m:
                # 取得年度欄位並進行縮放
                year_cols_to_scale = [col for col in df_pivot.columns if isinstance(col, int)]
                df_pivot[year_cols_to_scale] = df_pivot[year_cols_to_scale] / 1000.0
            
            df_bench = get_industry_benchmarks(df_proj, db_metric)
            if is_money_m and not df_bench.empty:
                df_bench[db_metric] = df_bench[db_metric] / 1000.0
            
            fig = go.Figure()
            year_cols = sorted([col for col in df_pivot.columns if isinstance(col, int)])
            for _, row in df_pivot.iterrows():
                fig.add_trace(go.Scatter(
                    x=year_cols, 
                    y=[row[y] for y in year_cols], 
                    name=f"{row['ticker']} {row['name']}", 
                    line=dict(width=5 if row['is_tested_party'] else 2)
                ))
            
            if not df_bench.empty:
                for ind in df_bench["industry_tag"].unique():
                    sub = df_bench[df_bench["industry_tag"] == ind].sort_values("year")
                    fig.add_trace(go.Scatter(x=sub["year"], y=sub[db_metric], name=f"🧬 {ind} 平均", line=dict(dash='dash')))
            
            fig.update_layout(yaxis=dict(title=f"{metric_option} ({unit_str})"))
            st.plotly_chart(fig, use_container_width=True)
            
            # 摘要卡片 (每行 3 個)
            # 注意：波動率也需配合縮放
            vol_series = calculate_volatility(df_proj, db_metric)
            if is_money_m: vol_series = vol_series / 1000.0
            
            num_comp = len(df_pivot)
            for i in range(0, num_comp, 3):
                row_items = df_pivot.iloc[i : i+3]
                cols = st.columns(3)
                for idx, (_, row) in enumerate(row_items.iterrows()):
                    ticker = row["ticker"]; name = row["name"]; is_tp = row["is_tested_party"]
                    y_vals = [row[y] for y in year_cols if pd.notna(row[y])]
                    avg_v = np.mean(y_vals) if y_vals else 0.0
                    vol_v = vol_series.get(ticker, 0.0)
                    card_style = "border: 2px solid #E74C3C;" if is_tp else "border: 1px solid #eee;"
                    with cols[idx]:
                        # 格式化數值顯示：金額指標顯示一位小數與千分位
                        if is_money_m:
                            display_val = f"{avg_v:,.1f}"
                        elif is_percentage:
                            display_val = f"{avg_v:.2f}"
                        else: # EPS
                            display_val = f"{avg_v:.2f}"
                        
                        st.markdown(f'<div class="metric-card" style="{card_style}"><div class="metric-label">{"受測企業" if is_tp else "可比同業"}</div><div style="font-weight:600;">{ticker} {name}</div><div class="metric-val">{display_val}{unit_str}</div><div class="metric-sub">SD: {vol_v:.2f}</div></div>', unsafe_allow_html=True)
            
            # --- 數據明細表格 ---
            st.markdown("---")
            st.markdown("#### 📋 財務比率/金額年度對照表")
            df_display = df_pivot.copy()
            df_display = df_display.rename(columns={"ticker": "股票代號", "name": "公司簡稱", "is_tested_party": "受測企業", "industry_tag": "產業分類"})
            for y in year_cols:
                if is_percentage:
                    df_display[y] = df_display[y].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "-")
                elif db_metric == "eps":
                    df_display[y] = df_display[y].map(lambda x: f"${x:.2f}" if pd.notna(x) else "-")
                elif is_money_m:
                    df_display[y] = df_display[y].map(lambda x: f"{x:,.1f} M" if pd.notna(x) else "-")
                else:
                    df_display[y] = df_display[y].map(lambda x: f"{x:,.0f} {unit_str}" if pd.notna(x) else "-")
            df_display["受測企業"] = df_display["受測企業"].map({True: "🎯 是", False: "⚖️ 否"})
            st.dataframe(df_display, use_container_width=True, hide_index=True)

elif st.session_state["active_tab"] == "公司深度分析":
    st.markdown('<h1 class="main-title">🎯 公司深度分析</h1>', unsafe_allow_html=True)
    if not selected_project_id:
        st.info("👋 請先選取專案。")
    else:
        df_proj = get_project_financial_df(selected_project_id)
        if df_proj.empty:
            st.warning("⚠️ 目前專案尚無數據。")
        else:
            comp_options = df_proj.groupby("ticker")["name"].first().to_dict()
            selected_ticker = st.selectbox("選擇分析公司", options=list(comp_options.keys()), format_func=lambda x: f"{x} {comp_options[x]}")
            
            if selected_ticker:
                df_comp = df_proj[df_proj["ticker"] == selected_ticker].sort_values("year")
                current_p, total_avg_p, yearly_avg_dict = get_stock_price_info(selected_ticker)
                
                c1, c2 = st.columns(2)
                c1.metric("即時股價", f"NT$ {current_p:.2f}")
                c2.metric("五年平均股價", f"NT$ {total_avg_p:.2f}")
                
                if yearly_avg_dict:
                    st.markdown("##### 📅 近五年逐年平均股價")
                    sorted_years = sorted(yearly_avg_dict.keys(), reverse=True)[:5]
                    p_cols = st.columns(len(sorted_years))
                    for i, year in enumerate(reversed(sorted_years)):
                        p_cols[i].markdown(f'<div style="text-align:center; padding:10px; border:1px solid #eee; border-radius:8px;"><div style="font-size:0.8rem; color:#666;">{year} Avg</div><div style="font-size:1.1rem; font-weight:700;">${yearly_avg_dict[year]:.1f}</div></div>', unsafe_allow_html=True)
                
                st.markdown("---")
                
                # 1. 財務比率趨勢圖 (含雙軸股價)
                st.markdown("#### 📈 獲利能力與股價對比")
                fig_ratio = go.Figure()
                for m, color in [("gross_margin", "#1abc9c"), ("operating_margin", "#3498db"), ("net_margin", "#9b59b6")]:
                    fig_ratio.add_trace(go.Scatter(x=df_comp["year"], y=df_comp[m], name=m, line=dict(color=color, width=3), mode='lines+markers'))
                
                if yearly_avg_dict:
                    plot_years = sorted(yearly_avg_dict.keys())
                    fig_ratio.add_trace(go.Scatter(x=plot_years, y=[yearly_avg_dict[y] for y in plot_years], name="年平均股價 (右軸)", line=dict(color="#e67e22", dash="dot"), yaxis="y2", mode='lines+markers'))
                
                fig_ratio.update_layout(yaxis=dict(title="比率 (%)"), yaxis2=dict(title="股價 (NT$)", overlaying="y", side="right"), legend=dict(orientation="h", y=1.15))
                st.plotly_chart(fig_ratio, use_container_width=True)
                
                # 2. 營運金額趨勢圖 (單位：百萬元)
                st.markdown("#### 💰 營運規模趨勢 (單位：百萬元)")
                fig_money = go.Figure()
                # 轉換單位：原資料庫為千元，除以 1000 變為百萬元
                money_metrics = [("revenue", "營業收入", "#2ecc71"), ("operating_cost", "營業成本", "#e74c3c"), ("operating_expenses", "營業費用", "#f39c12")]
                for m, label, color in money_metrics:
                    fig_money.add_trace(go.Bar(x=df_comp["year"], y=df_comp[m] / 1000.0, name=label, marker_color=color))
                
                fig_money.update_layout(barmode='group', yaxis=dict(title="金額 (百萬元 NTD)"), legend=dict(orientation="h", y=1.15))
                st.plotly_chart(fig_money, use_container_width=True)
                
                # 3. 數據表格 (整合金額指標與股價)
                st.markdown("#### 📋 綜合數據明細表")
                df_show = df_comp[["year", "revenue", "operating_cost", "operating_expenses", "gross_margin", "operating_margin", "net_margin", "eps"]].copy()
                
                # 單位轉換：千元 -> 百萬元
                df_show["revenue"] = df_show["revenue"] / 1000.0
                df_show["operating_cost"] = df_show["operating_cost"] / 1000.0
                df_show["operating_expenses"] = df_show["operating_expenses"] / 1000.0
                
                # 注入年度股價
                df_show["avg_price"] = df_show["year"].map(lambda x: yearly_avg_dict.get(x, 0.0))
                
                df_show.columns = ["年度", "營收(M)", "成本(M)", "費用(M)", "毛利(%)", "利益(%)", "純益(%)", "EPS", "年均價"]
                
                # 格式化顯示
                st.dataframe(
                    df_show.style.format({
                        "營收(M)": "{:,.1f}", "成本(M)": "{:,.1f}", "費用(M)": "{:,.1f}",
                        "毛利(%)": "{:.2f}%", "利益(%)": "{:.2f}%", "純益(%)": "{:.2f}%",
                        "EPS": "{:.2f}", "年均價": "{:.1f}"
                    }), 
                    use_container_width=True, hide_index=True
                )
