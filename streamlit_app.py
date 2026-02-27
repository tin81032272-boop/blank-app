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
    .badge-yellow { background-color: #F39C12; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

st.title("⚡ 台美雙臂：短線波段指揮中心")
st.caption("專注於均線動能與 RSI 乖離率。純數字自動判定為台股，英文字母判定為美股。")

tab1, tab2, tab3 = st.tabs(["🎯 短線技術面雷達", "💰 資金配置 (Total Intake)", "📓 進出場紀律帳本"])

# =====================================================
# TAB 1: 短線技術面雷達 
# =====================================================
with tab1:
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("### 🔍 鎖定標的")
        raw_symbol = st.text_input("輸入股票代號", value="TSLA", help="純數字自動加 .TW，美股請輸入代號 (如 TSLA)")
        period_select = st.selectbox("分析週期", ["1mo", "3mo", "6mo", "1y"], index=1)
        analyze_btn = st.button("啟動技術掃描 🚀", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🧮 盤中模擬試算")
        sim_entry = st.number_input("預計進場價", value=0.0, step=1.0, min_value=0.0)
        sim_shares = st.number_input("預計買入股數", value=100, step=10, min_value=1)
        
    with col2:
        if analyze_btn and raw_symbol:
            clean_symbol = raw_symbol.strip().upper()
            fetch_symbol = f"{clean_symbol}.TW" if clean_symbol.isdigit() and len(clean_symbol) == 4 else clean_symbol

            with st.spinner(f"正在抓取 {fetch_symbol} 即時數據..."):
                try:
                    ticker = yf.Ticker(fetch_symbol)
                    hist = ticker.history(period=period_select)
                    
                    if hist.empty:
                        st.error(f"找不到 {fetch_symbol} 的資料，請確認代碼是否正確（上櫃股票請手動加 .TWO）。")
                    else:
                        # 指標計算
                        hist['5MA'] = hist['Close'].rolling(window=5, min_periods=1).mean()
                        hist['10MA'] = hist['Close'].rolling(window=10, min_periods=1).mean()
                        hist['20MA'] = hist['Close'].rolling(window=20, min_periods=1).mean()
                        
                        delta = hist['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
                        rs = gain / loss
                        hist['RSI'] = 100 - (100 / (1 + rs))
                        hist['RSI'] = hist['RSI'].fillna(50)
                        
                        curr_price = hist['Close'].iloc[-1]
                        ma5 = hist['5MA'].iloc[-1]
                        ma10 = hist['10MA'].iloc[-1]
                        rsi_14 = hist['RSI'].iloc[-1]
                        
                        # AI 策略判定
                        if curr_price > ma5 and ma5 > ma10 and 40 < rsi_14 < 70:
                            action_signal = "<span class='badge-red'>🎯 買入 (BUY)</span> - 動能向上且未過熱"
                        elif curr_price < ma5 and rsi_14 > 60:
                            action_signal = "<span class='badge-green'>📉 獲利了結 (SELL)</span> - 跌破短均線"
                        elif rsi_14 > 75:
                            action_signal = "<span class='badge-green'>⚠️ 減碼 (REDUCE)</span> - RSI嚴重超買"
                        elif rsi_14 < 30 and curr_price > hist['Close'].iloc[-2]:
                            action_signal = "<span class='badge-yellow'>💡 試單 (SPECULATIVE)</span> - 超賣區反彈"
                        else:
                            action_signal = "<span class='badge-gray'>⏳ 觀望 (HOLD)</span> - 等待均線表態"

                        trend_status = "多頭強勢 ⬆" if curr_price > ma5 else ("空頭弱勢 ⬇" if curr_price < ma10 else "震盪整理 ↔")
                        
                        # 試算損益
                        sim_pnl_text = ""
                        if sim_entry > 0:
                            unrealized_pnl = (curr_price - sim_entry) * sim_shares
                            pnl_color = "#FF4B4B" if unrealized_pnl > 0 else "#00CC96"
                            sim_pnl_text = f"<br><b>📊 模擬損益：</b> <span style='color:{pnl_color}; font-weight:bold;'>${unrealized_pnl:,.2f}</span> (以 ${sim_entry} 進場 {sim_shares} 股)"

                        st.markdown(f"""
                        <div class="card">
                            <h3 style="margin-top:0; color:#00E5FF;">{fetch_symbol} 短線戰情報告</h3>
                            <b>即時現價：</b> ${curr_price:.2f} <br>
                            <b>動能狀態：</b> {trend_status} | <b>RSI (14)：</b> {rsi_14:.1f} <br>
                            <b>系統建議：</b> {action_signal}
                            {sim_pnl_text}
                            <hr style="border-color: #444;">
                            <b>🛡️ 防守線：</b> 做多請將 <b>${ma10:.2f} (10MA)</b> 設為最後防線，跌破無條件拔檔！
                        </div>
                        """, unsafe_allow_html=True)

                        # 繪圖
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
                        fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='K線'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['5MA'], line=dict(color='#FF4B4B', width=1), name='5MA'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['10MA'], line=dict(color='#00E5FF', width=1), name='10MA'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], line=dict(color='#F39C12', width=1.5), name='RSI'), row=2, col=1)
                        fig.add_hline(y=70, line_dash="dot", row=2, col=1, line_color="red")
                        fig.add_hline(y=30, line_dash="dot", row=2, col=1, line_color="green")

                        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
                        fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(t=20, b=20, l=0, r=0))
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"連線異常或代碼錯誤，請稍後再試。錯誤細節：{e}")

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
# TAB 3: 進出場紀律帳本 (強化防呆與統計)
# =====================================================
with tab3:
    st.markdown("### 📓 交易進出紀錄與績效追蹤")
    
    LOG_FILE = "swing_trade_log.csv"
    
    # 讀取或初始化資料
    if os.path.exists(LOG_FILE): 
        df_log = pd.read_csv(LOG_FILE)
    else: 
        df_log = pd.DataFrame({
            "進場日期": [datetime.now().strftime('%Y-%m-%d')], 
            "代號": ["TSLA"], 
            "方向": ["多"],
            "股數": [10.0],
            "進場價": [200.0],
            "停損點": [190.0],
            "出場價": [0.0],
            "已實現損益": [0.0],
            "進場理由": ["突破 5日線且 RSI 健康"]
        })

    # 使用 column_config 強制防呆，防止輸入文字導致計算崩潰
    st.markdown("👇 **直接在表格內點擊修改，系統會自動儲存與計算。**")
    edited_log = st.data_editor(
        df_log, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "股數": st.column_config.NumberColumn("股數", min_value=1, step=1),
            "進場價": st.column_config.NumberColumn("進場價", min_value=0.0, step=0.1, format="$ %.2f"),
            "停損點": st.column_config.NumberColumn("停損點", min_value=0.0, step=0.1, format="$ %.2f"),
            "出場價": st.column_config.NumberColumn("出場價 (未平倉填0)", min_value=0.0, step=0.1, format="$ %.2f"),
            "已實現損益": st.column_config.NumberColumn("已實現損益 (自動計算)", disabled=True, format="$ %.2f"),
        }
    )
    
    # 自動計算損益邏輯 (僅計算有出場價的欄位)
    mask_closed_long = (edited_log["方向"] == "多") & (edited_log["出場價"] > 0)
    mask_closed_short = (edited_log["方向"] == "空") & (edited_log["出場價"] > 0)
    
    edited_log.loc[mask_closed_long, "已實現損益"] = (edited_log["出場價"] - edited_log["進場價"]) * edited_log["股數"]
    edited_log.loc[mask_closed_short, "已實現損益"] = (edited_log["進場價"] - edited_log["出場價"]) * edited_log["股數"]
    
    # 若有變更則存檔
    if not edited_log.equals(df_log):
        edited_log.to_csv(LOG_FILE, index=False)
        st.success("✅ 資料已自動結算並存檔！")
        st.rerun() # 觸發畫面更新，讓損益數字立刻重算顯示
    
    # === 績效儀表板 ===
    st.markdown("---")
    st.markdown("#### 🏆 策略績效統整")
    
    # 篩選出已經平倉的交易
    closed_trades = edited_log[edited_log["出場價"] > 0]
    total_trades = len(closed_trades)
    
    if total_trades > 0:
        winning_trades = len(closed_trades[closed_trades["已實現損益"] > 0])
        win_rate = (winning_trades / total_trades) * 100
        total_profit = closed_trades["已實現損益"].sum()
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("已平倉總損益", f"${total_profit:,.2f}")
        col_m2.metric("策略勝率", f"{win_rate:.1f} %")
        col_m3.metric("完成交易總次數", f"{total_trades} 次")
    else:
        st.info("目前尚無已平倉（出場價大於 0）的交易紀錄，完成第一筆交易後將顯示績效統計。")
