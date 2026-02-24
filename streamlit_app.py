import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pytz
import os

st.set_page_config(page_title="波段紀律系統 4.0", page_icon="🚀", layout="wide")

st.title("🚀 波段紀律交易系統 4.0（專業自用版）")

tw_tz = pytz.timezone('Asia/Taipei')
now = datetime.now(tw_tz)
st.caption(f"系統時間：{now.strftime('%Y-%m-%d %H:%M')}")

tab1, tab2, tab3 = st.tabs(["🎯 個股診斷", "📊 交易紀錄", "🧪 回測與績效"])

# =====================================================
# 共用函數
# =====================================================

def smart_ticker_lookup(user_input):
    user_input = str(user_input).strip()
    if ".TW" in user_input.upper() or ".TWO" in user_input.upper():
        return user_input.upper()
    return user_input + ".TW"

@st.cache_data(ttl=600)
def market_filter():
    twii = yf.download("^TWII", period="3mo", progress=False)
    twii['20MA'] = twii['Close'].rolling(20).mean()
    twii['60MA'] = twii['Close'].rolling(60).mean()
    today = twii.iloc[-1]

    if today['Close'] > today['20MA'] > today['60MA']:
        return "多頭"
    elif today['Close'] > today['60MA']:
        return "震盪"
    else:
        return "空頭"

def calculate_indicators(hist):

    hist['5MA'] = hist['Close'].rolling(5).mean()
    hist['10MA'] = hist['Close'].rolling(10).mean()
    hist['20MA'] = hist['Close'].rolling(20).mean()

    exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
    exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
    hist['MACD'] = exp1 - exp2
    hist['Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()

    delta = hist['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    loss = loss.replace(0, 1e-10)
    rs = gain / loss
    hist['RSI'] = 100 - (100 / (1 + rs))

    hist['prev_close'] = hist['Close'].shift(1)
    tr1 = hist['High'] - hist['Low']
    tr2 = (hist['High'] - hist['prev_close']).abs()
    tr3 = (hist['Low'] - hist['prev_close']).abs()
    hist['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    hist['ATR'] = hist['TR'].rolling(14).mean()

    hist['Turnover'] = hist['Close'] * hist['Volume']

    return hist

def position_size(capital, entry, stop):
    risk_per_trade = capital * 0.02
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return 0
    return int(risk_per_trade // risk_per_share)

# =====================================================
# TAB 1 個股診斷
# =====================================================

with tab1:

    market_status = market_filter()

    if market_status == "空頭":
        st.error("⚠ 大盤空頭，請降低出手頻率")
    else:
        st.success(f"📈 大盤狀態：{market_status}")

    col1, col2 = st.columns([3,1])
    user_input = col1.text_input("輸入代號", value="2330")
    btn = col2.button("執行診斷")

    capital_input = st.number_input("可用資金", value=50000)

    if btn:

        parsed = smart_ticker_lookup(user_input)

        hist = yf.download(parsed, period="6mo", progress=False)
        hist = calculate_indicators(hist)

        today = hist.iloc[-1]

        # 週線濾網
        weekly = yf.download(parsed, period="8mo", interval="1wk", progress=False)
        weekly['20MA'] = weekly['Close'].rolling(20).mean()

        if weekly.iloc[-1]['Close'] < weekly.iloc[-1]['20MA']:
            st.error("❌ 週線空頭，不建議進場")
            st.stop()

        # 評分模型
        score = 0

        if today['5MA'] > today['10MA'] > today['20MA']:
            score += 30

        score += ((today['Close'] - today['20MA']) / today['20MA']) * 100
        score += (today['MACD'] - today['Signal']) * 5

        if 50 < today['RSI'] < 70:
            score += 10
        elif today['RSI'] > 80:
            score -= 20

        avg_vol = hist['Volume'].rolling(5).mean().shift(1).iloc[-1]
        if avg_vol > 0:
            score += (today['Volume'] / avg_vol) * 5

        recent_high = hist['High'].rolling(20).max().shift(1).iloc[-1]
        breakout = today['Close'] > recent_high

        if breakout:
            score += 25

        if today['Turnover'] < 100_000_000:
            score -= 20

        entry = today['Close']
        stop = today['20MA'] * 0.99
        target = entry + today['ATR'] * 2.5
        shares = position_size(capital_input, entry, stop)

        if score > 60:
            advice = "🟢 可做多"
        elif score > 40:
            advice = "🟡 等拉回"
        else:
            advice = "🔴 不建議"

        st.markdown(f"""
        ### 📊 診斷報告
        AI 評分：{round(score,2)}  
        建議：**{advice}**

        進場：{round(entry,1)}  
        停損：{round(stop,1)}  
        停利：{round(target,1)}  
        建議股數：{shares} 股
        """)

        # 紀律檢查
        st.markdown("### 🧠 紀律檢查")
        flags = []

        if market_status == "空頭":
            flags.append("大盤空頭")

        if today['RSI'] > 80:
            flags.append("RSI過熱")

        if today['Close'] < today['20MA']:
            flags.append("跌破月線")

        if flags:
            for f in flags:
                st.error(f"⚠ {f}")
        else:
            st.success("符合紀律")

        # K線圖
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close']
        ))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['20MA'], name='20MA'))
        st.plotly_chart(fig, use_container_width=True)

# =====================================================
# TAB 2 交易紀錄
# =====================================================

with tab2:

    LOG_FILE = "trade_log.csv"

    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
    else:
        df = pd.DataFrame({
            "日期":[datetime.now().strftime('%Y-%m-%d')],
            "損益":[0]
        })

    edited = st.data_editor(df, num_rows="dynamic")

    if not edited.equals(df):
        edited.to_csv(LOG_FILE, index=False)
        st.success("已儲存")

# =====================================================
# TAB 3 回測與績效
# =====================================================

with tab3:

    st.markdown("## 🧪 策略回測")

    ticker = st.text_input("回測代號", value="2330")

    if st.button("執行回測"):

        parsed = smart_ticker_lookup(ticker)
        hist = yf.download(parsed, period="6mo", progress=False)
        hist = calculate_indicators(hist)

        results = []
        position = 0
        entry_price = 0

        for i in range(50, len(hist)):
            today = hist.iloc[i]
            recent_high = hist['High'].rolling(20).max().shift(1).iloc[i]

            if position == 0:
                if (
                    today['Close'] > recent_high and
                    today['5MA'] > today['10MA'] > today['20MA'] and
                    50 < today['RSI'] < 75
                ):
                    position = 1
                    entry_price = today['Close']

            else:
                stop = today['20MA'] * 0.99
                if today['Close'] < stop:
                    results.append(today['Close'] - entry_price)
                    position = 0

        if results:
            win = len([r for r in results if r > 0])
            win_rate = win / len(results) * 100
            avg = sum(results)/len(results)

            st.metric("交易次數", len(results))
            st.metric("勝率", f"{win_rate:.1f}%")
            st.metric("平均每筆報酬", f"{avg:.2f}")
        else:
            st.warning("沒有產生交易訊號")
