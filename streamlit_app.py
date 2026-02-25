import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import os

# =====================================================
# 頁面設定與自訂 CSS
# =====================================================
st.set_page_config(page_title="短線波段指揮中心", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .big-font { font-size:22px !important; font-weight: bold; color: #00E5FF; }
    .card { background-color: #1E1E1E; color: white; padding: 18px; border-radius: 12px; border-left: 6px solid #00E5FF; margin-bottom: 10px;}
    .badge-red { background-color: #FF4B4B; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-green { background-color: #00CC96; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-gray { background-color: #555555; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

st.title("⚡ 台美雙臂：短線波段指揮中心")
st.caption("專注於均線動能與 RSI 乖離率。純數字自動判定為台股，英文字母判定為美股。")

tab1, tab2, tab3 = st.tabs(["🎯 短線技術面雷達", "💰 資金配置 (Total Intake)", "📓 進出場紀律帳本"])

# =====================================================
# TAB 1: 短線技術面雷達 (防呆與自動化處理)
# =====================================================
with tab1:
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("### 🔍 鎖定標的")
        raw_symbol = st.text_input("輸入股票代號", value="2330", help="輸入純數字自動加 .TW，或輸入美股代號如 NVDA")
        period_select = st.selectbox("分析週期", ["1mo", "3mo", "6mo", "1y"], index=1)
        analyze_btn = st.button("啟動技術掃描 🚀", type="primary", use_container_width=True)
        
    with col2:
        if analyze_btn and raw_symbol:
            # 智慧代號處理：若是純數字且為 4 碼，自動補上 .TW
            clean_symbol = raw_symbol.strip().upper()
            if clean_symbol.isdigit() and len(clean_symbol) == 4:
                fetch_symbol = f"{clean_symbol}.TW"
            else:
                fetch_symbol = clean_symbol

            with st.spinner(f"正在抓取 {fetch_symbol} 即時數據..."):
                try:
                    ticker = yf.Ticker(fetch_symbol)
                    hist = ticker.history(period=period_select)
                    
                    if hist.empty:
                        st.error(f"找不到 {fetch_symbol} 的資料。若為上櫃股票請手動加上 '.TWO' (例如: 8069.TWO)。")
                    else:
                        # 安全計算均線 (避免新上市股票資料不足報錯)
                        hist['5MA'] = hist['Close'].rolling(window=5, min_periods=1).mean()
                        hist['10MA'] = hist['Close'].rolling(window=10, min_periods=1).mean()
                        hist['20MA'] = hist['Close'].rolling(window=20, min_periods=1).mean()
                        
                        # 安全計算 RSI (14)
                        delta = hist['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
                        rs = gain / loss
                        hist['RSI'] = 100 - (100 / (1 + rs))
                        hist['RSI'] = hist['RSI'].fillna(50) # 防呆：補齊初始 NaN
                        
                        curr_price = hist['Close'].iloc[-1]
                        ma5 = hist['5MA'].iloc[-1]
                        ma10 = hist['10MA'].iloc[-1]
                        rsi_14 = hist['RSI'].iloc[-1]
                        
                        # 短線動能判定邏輯
                        trend_status = ""
                        if curr_price > ma5 and ma5 > ma10:
                            trend_status = "<span class='badge-red'>多頭強勢 ⬆</span> (沿 5 日線上攻)"
                        elif curr_price < ma5 and ma5 < ma10:
                            trend_status = "<span class='badge-green'>空頭弱勢 ⬇</span> (跌破 5 日線)"
                        else:
                            trend_status = "<span class='badge-gray'>震盪整理 ↔</span> (等待均線表態)"
                            
                        rsi_status = "正常"
                        if rsi_14 > 70: rsi_status = "⚠️ 過熱 (防範拉回)"
                        elif rsi_14 < 30: rsi_status = "💡 超賣 (注意反彈)"

                        st.markdown(f"""
                        <div class="card">
                            <h3 style="margin-top:0; color:#00E5FF;">{fetch_symbol} 短線戰情報告</h3>
                            <b>即時現價：</b> ${curr_price:.2f} <br>
                            <b>動能狀態：</b> {trend_status} <br>
                            <b>RSI (14)：</b> {rsi_14:.1f} ({rsi_status}) <br>
                            <hr style="border-color: #444;">
                            <b>🎯 防守建議：</b> 做多者將 <b>10日線 (${ma10:.2f})</b> 或 <b>5日線 (${ma5:.2f})</b> 設為移動停損點。跌破即拔檔！
                        </div>
                        """, unsafe_allow_html=True)

                        # 繪製 K 線圖 + 均線 + RSI (去除週末斷層)
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
                        
                        fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='K線'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['5MA'], line=dict(color='#FF4B4B', width=1), name='5MA (短線動能)'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['10MA'], line=dict(color='#00E5FF', width=1), name='10MA (短線防守)'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['20MA'], line=dict(color='#F39C12', width=1, dash='dot'), name='20MA (月線生命)'), row=1, col=1)
                        
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], line=dict(color='#F39C12', width=1.5), name='RSI'), row=2, col=1)
                        fig.add_hline(y=70, line_dash="dot", row=2, col=1, line_color="red")
                        fig.add_hline(y=30, line_dash="dot", row=2, col=1, line_color="green")

                        # 隱藏週末，讓線圖連貫
                        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
                        
                        fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(t=20, b=20, l=0, r=0))
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"系統異常，請稍後再試或確認網路連線。錯誤代碼：{e}")

# =====================================================
# TAB 2: 短線作戰資金池 (Total Intake 表格)
# =====================================================
with tab2:
    st.markdown("### 💰 單筆資金配置表")
    st.write("短線操作切忌單支個股重壓。將單筆資金切分為美股、台股與保留現金。")
    
    intake_levels = [50000, 100000, 300000, 500000, 1000000]
    
    table_md = """
| 每月總投入 (Total Intake) | 美股動能部位 (40%) | 台股波段部位 (40%) | 現金保留水位 (20%) |
| :--- | :--- | :--- | :--- |
"""
    for intake in intake_levels:
        table_md += f"| **{intake:,} 元** | {intake * 0.4:,.0f} 元 | {intake * 0.4:,.0f} 元 | {intake * 0.2:,.0f} 元 |\n"
    
    st.markdown(table_md)
    st.info("💡 **紀律提醒**：動用保留現金的前提是「大盤錯殺引發超跌反彈」，而非「為了攤平虧損的爛倉位」。")

# =====================================================
# TAB 3: 進出場紀律帳本 (強化容錯)
# =====================================================
with tab3:
    st.markdown("### 📓 交易進出紀錄")
    
    LOG_FILE = "swing_trade_log.csv"
    if os.path.exists(LOG_FILE): 
        # 強制指定型態，避免讀取錯誤
        df_log = pd.read_csv(LOG_FILE)
    else: 
        df_log = pd.DataFrame({
            "進場日期": [datetime.now().strftime('%Y-%m-%d')], 
            "代號": ["2330"], 
            "方向": ["多"],
            "進場價": [1000.0],
            "停損點": [980.0],
            "出場價": [0.0],
            "已實現損益(NTD)": [0.0],
            "進場理由": ["突破 5日線"]
        })

    edited_log = st.data_editor(df_log, num_rows="dynamic", use_container_width=True)
    
    if not edited_log.equals(df_log):
        edited_log.to_csv(LOG_FILE, index=False)
        st.success("✅ 交易紀錄已更新並自動存檔！")
    
    # 強制轉為數值，若輸入錯誤文字則轉為 0，避免崩潰
    edited_log["已實現損益(NTD)"] = pd.to_numeric(edited_log["已實現損益(NTD)"], errors='coerce').fillna(0)
    total_profit = edited_log["已實現損益(NTD)"].sum()
    
    st.metric("短線累計總損益", f"NT$ {total_profit:,.0f}")
