import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz
import os

st.set_page_config(page_title="波段紀律系統 5.0", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .report-card { background-color: #1E1E1E; color: white; padding: 20px; border-radius: 12px; border-top: 5px solid #1E90FF; margin-top: 15px; }
    .metric-box { background-color: #2b2b2b; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #444;}
    .news-box { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 5px solid #FFD700; margin-top: 10px; font-size: 14px;}
    .highlight-red { color: #FF4B4B; font-weight: bold; }
    .highlight-green { color: #00CC96; font-weight: bold; }
    .card { background-color: #2b2b2b; padding: 15px; border-radius: 10px; border-left: 5px solid #00CC96; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 置頂控制區與一鍵更新
# =====================================================
colA, colB = st.columns([3, 1])
with colA:
    st.title("🚀 波段紀律交易系統 5.0（全自動旗艦版）")
with colB:
    st.write("") 
    if st.button("🔄 一鍵更新盤況與選股", type="primary", use_container_width=True):
        st.cache_data.clear()

tw_tz = pytz.timezone('Asia/Taipei')
now = datetime.now(tw_tz)
st.caption(f"系統時間：{now.strftime('%Y-%m-%d %H:%M')} | 內建自動選股雷達與即時消息面分析")

# =====================================================
# 共用核心函數
# =====================================================
def smart_ticker_lookup(user_input):
    user_input = str(user_input).strip()
    if ".TW" in user_input.upper() or ".TWO" in user_input.upper():
        return user_input.upper()
    return user_input + ".TW"

@st.cache_data(ttl=600)
def market_filter():
    try:
        twii = yf.download("^TWII", period="3mo", progress=False)
        if isinstance(twii.columns, pd.MultiIndex): twii.columns = twii.columns.droplevel(1)
            
        twii['20MA'] = twii['Close'].rolling(20).mean()
        twii['60MA'] = twii['Close'].rolling(60).mean()
        today = twii.iloc[-1]

        if today['Close'] > today['20MA'] > today['60MA']: return "🟢 大盤多頭 (積極作多)"
        elif today['Close'] > today['60MA']: return "🟡 大盤震盪 (縮小部位)"
        else: return "🔴 大盤空頭 (嚴格觀望)"
    except:
        return "⚪ 大盤數據讀取中"

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
    hist['Recent_High20'] = hist['High'].rolling(20).max().shift(1)
    return hist

def position_size(capital, entry, stop):
    risk_per_trade = capital * 0.02
    risk_per_share = entry - stop
    if risk_per_share <= 0: return 0
    return int(risk_per_trade // risk_per_share)

# 觀測池 (波段強勢題材)
strategic_pool = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2382.TW": "廣達", "3231.TW": "緯創",
    "2376.TW": "技嘉", "1519.TW": "華城", "1513.TW": "中興電", "1504.TW": "東元", "1514.TW": "亞力",
    "2603.TW": "長榮", "2609.TW": "陽明", "2618.TW": "長榮航", "2365.TW": "昆盈", "3324.TW": "雙鴻",
    "3017.TW": "奇鋐", "3034.TW": "聯詠", "3443.TW": "創意", "3661.TW": "世芯-KY", "3450.TW": "聯鈞"
}

# 顯示大盤狀態
market_status = market_filter()
if "空頭" in market_status: st.error(f"⚠ {market_status}：覆巢之下無完卵，系統建議空手觀望。")
elif "震盪" in market_status: st.warning(f"⚖️ {market_status}：突破訊號易騙線，建議買拉回。")
else: st.success(f"📈 {market_status}：趨勢確立，可利用選股雷達積極操作。")

tab1, tab2, tab3, tab4 = st.tabs(["🎯 AI 自動選股雷達", "🏥 個股診斷與消息面", "📊 交易紀錄", "🧪 策略回測與績效"])

# =====================================================
# TAB 1: AI 自動選股雷達
# =====================================================
with tab1:
    st.markdown("### 🤖 盤面強勢股自動掃描")
    st.caption("策略邏輯：過濾站上均線、RSI健康、且具備爆發動能的優質股。")
    
    capital_input = st.number_input("設定雷達波段總資金 (用於2%風控)", value=500000, step=50000)
    
    @st.cache_data(ttl=600)
    def auto_screener(pool):
        results = []
        for sym, name in pool.items():
            try:
                hist = yf.download(sym, period="6mo", progress=False)
                if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.droplevel(1)
                if len(hist) < 30: continue
                
                hist = calculate_indicators(hist)
                today = hist.iloc[-1]
                
                # 嚴格選股條件
                if today['Close'] < today['20MA']: continue # 跌破月線不看
                if today['RSI'] > 80 or today['RSI'] < 40: continue # 過熱或太弱不看
                
                score = 0
                if today['5MA'] > today['10MA'] > today['20MA']: score += 30
                if today['MACD'] > today['Signal']: score += 20
                if today['Close'] > today['Recent_High20']: score += 20
                
                if score >= 40: # 達標才列入
                    entry = today['Close']
                    stop = today['20MA'] * 0.99
                    shares = position_size(capital_input, entry, stop)
                    
                    results.append({
                        "代號": sym.replace(".TW",""), "名稱": name, "現價": entry, 
                        "停損": stop, "建議股數": shares, "評分": score
                    })
            except: pass
        return sorted(results, key=lambda x: x['評分'], reverse=True)

    if st.button("🚀 啟動自動選股", type="primary"):
        with st.spinner("AI 海選全市場中，請稍候..."):
            targets = auto_screener(strategic_pool)
            if targets:
                st.success(f"篩選完成！為您挑選出 {len(targets)} 檔強勢股：")
                for t in targets:
                    st.markdown(f"""
                    <div class="card">
                        <h4>{t['名稱']} ({t['代號']}) <span style='float:right; font-size:16px; color:#1E90FF;'>AI評分: {t['評分']}</span></h4>
                        現價: <span class="highlight-red">${t['現價']:.1f}</span> | 
                        防守月線: <span class="highlight-green">${t['停損']:.1f}</span> | 
                        2%風控建議買進: <b>{t['建議股數']} 股</b>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("目前盤面無符合高勝率條件之標的，請耐心等待。")

# =====================================================
# TAB 2: 個股診斷與消息面
# =====================================================
with tab2:
    col1, col2 = st.columns([3, 1])
    user_input = col1.text_input("輸入欲診斷股票代號", value="2330")
    btn = col2.button("執行深度診斷與查新聞", type="primary", use_container_width=True)

    if btn:
        parsed = smart_ticker_lookup(user_input)
        with st.spinner("AI 診斷與爬取最新消息中..."):
            # 1. 抓技術面
            hist = yf.download(parsed, period="6mo", progress=False)
            if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.droplevel(1)
            
            # 2. 抓消息面
            try:
                ticker_info = yf.Ticker(parsed)
                news_data = ticker_info.news
            except:
                news_data = []

            if not hist.empty:
                hist = calculate_indicators(hist)
                today = hist.iloc[-1]

                weekly = yf.download(parsed, period="8mo", interval="1wk", progress=False)
                if isinstance(weekly.columns, pd.MultiIndex): weekly.columns = weekly.columns.droplevel(1)
                weekly['20MA'] = weekly['Close'].rolling(20).mean()
                week_trend_ok = weekly.iloc[-1]['Close'] >= weekly.iloc[-1]['20MA']

                score = 0
                if today['5MA'] > today['10MA'] > today['20MA']: score += 30
                score += ((today['Close'] - today['20MA']) / today['20MA']) * 100
                score += (today['MACD'] - today['Signal']) * 5
                if 50 < today['RSI'] < 70: score += 10
                elif today['RSI'] > 80: score -= 20
                if today['Close'] > today['Recent_High20']: score += 25

                entry = today['Close']
                stop = today['20MA'] * 0.99
                target = entry + today['ATR'] * 2.5
                shares = position_size(capital_input, entry, stop)

                if not week_trend_ok: advice, color = "🔴 嚴格禁止作多 (週線為空頭格局)", "#FF4B4B"
                elif score > 60: advice, color = "🟢 建議佈局做多 (動能強勁)", "#00CC96"
                elif score > 40: advice, color = "🟡 建議等待拉回 (靠近均線再行評估)", "#FFD700"
                else: advice, color = "🔴 不建議進場 (動能疲弱)", "#FF4B4B"

                flags = []
                if "空頭" in market_status: flags.append("大盤目前為空頭格局")
                if today['RSI'] > 80: flags.append("短線 RSI 過熱")
                if today['Close'] < today['20MA']: flags.append("股價跌破生命月線")
                if not week_trend_ok: flags.append("長線 (週 20MA) 趨勢向下")

                # 顯示診斷卡片
                st.markdown(f"""
                <div class="report-card">
                    <h3 style="margin-top:0;">{parsed.replace('.TW','')} 戰術診斷報告</h3>
                    <div style="background-color: {color}22; border-left: 5px solid {color}; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                        <span style="font-size: 18px; color: {color}; font-weight: bold;">{advice} (AI 評分: {score:.1f})</span>
                    </div>
                    
                    <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                        <div class="metric-box" style="flex: 1;"><b>建議進場價</b><br><span style="color:#1E90FF; font-size:18px;">${entry:.1f}</span></div>
                        <div class="metric-box" style="flex: 1;"><b>防守停損價</b><br><span style="color:#00CC96; font-size:18px;">${stop:.1f}</span></div>
                        <div class="metric-box" style="flex: 1;"><b>波段目標價</b><br><span style="color:#FF4B4B; font-size:18px;">${target:.1f}</span></div>
                        <div class="metric-box" style="flex: 1;"><b>2%風控可買</b><br><span style="color:#FFD700; font-size: 18px; font-weight: bold;">{shares} 股</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if flags:
                    st.markdown("#### 🧠 違規紀律檢查")
                    for f in flags: st.error(f"⚠ {f}")
                else:
                    st.success("✅ 目前技術面與大盤皆符合做多紀律！")

                # --- 新增：即時新聞面分析 ---
                st.markdown("#### 📰 最新消息面追蹤")
                if news_data:
                    for n in news_data[:5]: # 取最新 5 則
                        try:
                            pub_time = datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d %H:%M')
                            st.markdown(f"""
                            <div class="news-box">
                                <span style="color: #888;">{pub_time} ({n.get('publisher', 'Yahoo Finance')})</span><br>
                                <a href="{n['link']}" target="_blank" style="color: #FFF; text-decoration: none; font-weight: bold; font-size: 16px;">{n['title']}</a>
                            </div>
                            """, unsafe_allow_html=True)
                        except: pass
                else:
                    st.info("目前系統未爬取到近期重大新聞。")

                st.markdown("---")
                # K 線圖
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='日K'))
                fig.add_trace(go.Scatter(x=hist.index, y=hist['20MA'], name='20MA (月線)', line=dict(color='#9B59B6', width=2)))
                fig.update_layout(height=450, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

# =====================================================
# TAB 3 & 4: 交易紀錄與回測 (維持穩定版)
# =====================================================
with tab3:
    LOG_FILE = "trade_log.csv"
    if os.path.exists(LOG_FILE): df = pd.read_csv(LOG_FILE)
    else: df = pd.DataFrame({"日期":[datetime.now().strftime('%Y-%m-%d')], "標的":["2330"], "損益":[0]})

    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if not edited.equals(df):
        edited.to_csv(LOG_FILE, index=False)
        st.success("✅ 交易紀錄已儲存")

with tab4:
    st.markdown("### 🧪 策略回測中心")
    col_t1, col_t2 = st.columns([3, 1])
    ticker_bt = col_t1.text_input("輸入欲回測代號", value="2330", key="bt_ticker")
    if col_t2.button("🚀 執行高速回測", use_container_width=True):
        parsed = smart_ticker_lookup(ticker_bt)
        with st.spinner("執行回測中..."):
            hist = yf.download(parsed, period="2y", progress=False)
            if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.droplevel(1)
            hist = calculate_indicators(hist)
            results = []
            position = 0
            entry_price = 0

            for i in range(50, len(hist)):
                today = hist.iloc[i]
                recent_high = today['Recent_High20'] 

                if position == 0:
                    if (today['Close'] > recent_high and today['5MA'] > today['10MA'] > today['20MA'] and 50 < today['RSI'] < 75):
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
                avg_profit = sum(results) / len(results)
                total_profit = sum(results)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("歷史交易次數", f"{len(results)} 次")
                c2.metric("策略勝率", f"{win_rate:.1f}%")
                c3.metric("單次平均報酬 (價差)", f"${avg_profit:.2f}")
                c4.metric("總創造價差", f"${total_profit:.2f}")
            else:
                st.warning("此區間內沒有產生符合條件的交易訊號。")
