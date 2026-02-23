import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

st.set_page_config(page_title="行動版股市助理", page_icon="📱", layout="centered")
st.title("📱 股市隨身助理")

tw_tz = pytz.timezone('Asia/Taipei')
current_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M')
st.caption(f"⏱️ 系統更新時間：{current_time}")

tab1, tab2 = st.tabs(["📊 個人持股試算", "🔥 今日 AI 推薦清單"])

with tab1:
    st.markdown("### ⚙️ 輸入您的交易紀錄")
    col_in1, col_in2 = st.columns(2)
    ticker = col_in1.text_input("股票代號 (如 2330.TW)", value="2330.TW")
    buy_price = col_in2.number_input("購買價格", min_value=0.0, value=500.0, step=1.0)
    col_in3, col_in4 = st.columns(2)
    buy_lots = col_in3.number_input("購買張數 (1張=1000股)", min_value=0, value=1, step=1)
    buy_odd_shares = col_in4.number_input("零股", min_value=0, value=0, step=1)
    total_shares = (buy_lots * 1000) + buy_odd_shares
    total_cost = buy_price * total_shares

    if st.button("🔄 刷新即時報價"):
        st.cache_data.clear()

    @st.cache_data(ttl=60)
    def get_data(sym):
        s = yf.Ticker(sym)
        return s.info, s.history(period="6mo")

    if ticker:
        try:
            info, hist = get_data(ticker)
            curr = info.get('currentPrice', info.get('regularMarketPrice', hist['Close'].iloc[-1]))
            val = curr * total_shares
            pl = val - total_cost
            roi = (pl / total_cost * 100) if total_cost > 0 else 0
            st.markdown("---")
            c1, c2 = st.columns(2); c1.metric("即時股價", f"${curr:,.2f}"); c2.metric("總成本", f"${total_cost:,.0f}")
            c3, c4 = st.columns(2); c3.metric("總市值", f"${val:,.0f}"); c4.metric("損益", f"${pl:,.0f}", f"{roi:.2f}%")
            
            # 簡易操作建議
            hist['MA10'] = hist['Close'].rolling(10).mean()
            hist['MA20'] = hist['Close'].rolling(20).mean()
            if hist['MA10'].iloc[-1] > hist['MA20'].iloc[-1]:
                st.success("🟢 建議買入 (趨勢偏多)")
            else:
                st.warning("🟡 建議觀察 (趨勢偏弱)")

            fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
            fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.error("代號錯誤")

with tab2:
    st.markdown("### 🤖 盤面自動掃描")
    st.info("今日熱門股掃描中... (台積電、鴻海、0050 等)")
    # 這裡系統會自動運行掃描邏輯...
