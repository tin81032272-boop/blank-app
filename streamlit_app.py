import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pytz
import os

st.set_page_config(page_title="波段紀律系統 6.0", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .big-font { font-size:22px !important; font-weight: bold; color: #1E90FF; }
    .report-card { background-color: #1E1E1E; color: white; padding: 20px; border-radius: 12px; border-top: 5px solid #1E90FF; margin-top: 15px; }
    .metric-box { background-color: #2b2b2b; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #444;}
    .news-box { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 5px solid #FFD700; margin-top: 10px; font-size: 14px;}
    .highlight-red { color: #FF4B4B; font-weight: bold; }
    .highlight-green { color: #00CC96; font-weight: bold; }
    .highlight-blue { color: #1E90FF; font-weight: bold; }
    .card { background-color: #f8f9fa; color: #333; padding: 18px; border-radius: 12px; border-left: 6px solid #FF8C00; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);}
    .badge-red { background-color: #FF4B4B; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-green { background-color: #00CC96; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-gold { background-color: #FFD700; color: #333; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 置頂控制區與一鍵更新
# =====================================================
colA, colB = st.columns([3, 1])
with colA:
    st.title("🚀 波段紀律交易系統 6.0（實戰封測版）")
with colB:
    st.write("") 
    if st.button("🔄 一鍵更新盤況與選股", type="primary", use_container_width=True):
        st.cache_data.clear()

tw_tz = pytz.timezone('Asia/Taipei')
now = datetime.now(tw_tz)
st.caption(f"系統時間：{now.strftime('%Y-%m-%d %H:%M')} | 核心優化：底層防呆機制與回測視覺化")

# =====================================================
# 共用核心函數 (強化防呆與效能)
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
        if twii.empty: return "⚪ 大盤數據讀取異常"
        if isinstance(twii.columns, pd.MultiIndex): twii.columns = twii.columns.droplevel(1)
            
        twii['20MA'] = twii['Close'].rolling(20).mean()
        twii['60MA'] = twii['Close'].rolling(60).mean()
        today = twii.iloc[-1]

        if today['Close'] > today['20MA'] > today['60MA']: return "🟢 大盤多頭 (積極作多)"
        elif today['Close'] > today['60MA']: return "🟡 大盤震盪 (縮小部位)"
        else: return "🔴 大盤空頭 (嚴格觀望)"
    except:
        return "⚪ 大盤數據讀取異常"

def calculate_indicators(hist):
    hist = hist.copy() # 避免 Pandas SettingWithCopyWarning
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

# 觀測池 (擴增至 30 檔高流動性標的)
strategic_pool = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2382.TW": "廣達", "3231.TW": "緯創",
    "2376.TW": "技嘉", "1519.TW": "華城", "1513.TW": "中興電", "1504.TW": "東元", "1514.TW": "亞力",
    "2603.TW": "長榮", "2609.TW": "陽明", "2618.TW": "長榮航", "2365.TW": "昆盈", "3324.TW": "雙鴻",
    "3017.TW": "奇鋐", "3034.TW": "聯詠", "3443.TW": "創意", "3661.TW": "世芯-KY", "3450.TW": "聯鈞",
    "3081.TWO": "聯亞", "4979.TW": "華星光", "2359.TW": "所羅門", "2353.TW": "宏碁", "2324.TW": "仁寶",
    "2357.TW": "華碩", "0050.TW": "台灣50", "0056.TW": "高股息", "2881.TW": "富邦金", "2891.TW": "中信金"
}

market_status = market_filter()
if "空頭" in market_status: st.error(f"⚠ {market_status}：覆巢之下無完卵，系統建議空手觀望。")
elif "震盪" in market_status: st.warning(f"⚖️ {market_status}：突破訊號易騙線，建議買拉回。")
else: st.success(f"📈 {market_status}：趨勢確立，可利用選股雷達積極操作。")

tab1, tab2, tab3, tab4 = st.tabs(["🎯 AI 自動選股雷達", "🏥 個股診斷與消息面", "📊 實戰交易紀錄", "🧪 策略回測中心"])

# =====================================================
# TAB 1: AI 自動選股雷達
# =====================================================
with tab1:
    st.markdown("### 🤖 盤面強勢股自動掃描")
    capital_input = st.number_input("設定雷達波段總資金 (用於2%風控)", value=500000, step=50000)
    
    @st.cache_data(ttl=600)
    def auto_screener(pool):
        results = []
        for sym, name in pool.items():
            try:
                hist = yf.download(sym, period="6mo", progress=False)
                if hist.empty: continue
                if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.droplevel(1)
                if len(hist) < 30: continue
                
                hist = calculate_indicators(hist)
                today = hist.iloc[-1]
                
                # 嚴格選股過濾
                if today['Close'] < today['20MA']: continue 
                if today['RSI'] > 80 or today['RSI'] < 40: continue 
                
                score = 0
                if today['5MA'] > today['10MA'] > today['20MA']: score += 30
                if today['MACD'] > today['Signal']: score += 20
                if today['Close'] > today['Recent_High20']: score += 20
                
                # 成交量濾網 (避免死水股)
                avg_vol_5d = hist['Volume'].rolling(5).mean().shift(1).iloc[-1]
                if avg_vol_5d > 0 and today['Volume'] > avg_vol_5d * 1.2: score += 10
                
                if score >= 40: 
                    entry = today['Close']
                    stop = today['20MA'] * 0.99
                    shares = position_size(capital_input, entry, stop)
                    if shares < 1: continue

                    win_days = (hist['High'] - hist['Open']) / hist['Open'] >= 0.01 
                    win_rate = (win_days.sum() / len(win_days)) * 100
                    
                    atr = today['ATR']
                    buy_price = entry - (atr * 0.15) 
                    tp = entry + (atr * 3) 
                    
                    trade_value = shares * buy_price
                    est_gross_profit = shares * (tp - buy_price)
                    
                    fee = max(1, int(trade_value * 0.001425 * 0.28))
                    tax = int(trade_value * 0.003)
                    friction = (fee * 2) + tax
                    net_profit = est_gross_profit - friction
                    
                    if net_profit <= 0: continue
                    ev = (win_rate/100 * est_gross_profit) - ((1 - win_rate/100) * (shares * (buy_price - stop)))
                    
                    prev_close = hist['Close'].shift(1).iloc[-1]
                    status_badge = "<span class='badge-red'>今日強勢 ⬆</span>" if today['Close'] > prev_close else "<span class='badge-green'>今日拉回 ⬇</span>"
                    clean_sym = sym.replace('.TW', '').replace('.TWO', '')
                    
                    results.append({
                        "代號": sym, "clean_sym": clean_sym, "名稱": name, "現價": entry, 
                        "buy_price": buy_price, "停損": stop, "tp": tp, "建議股數": shares, 
                        "評分": score, "win_rate": win_rate, "net_profit": net_profit, 
                        "friction": friction, "ev": ev, "status": status_badge
                    })
            except: pass
        return sorted(results, key=lambda x: x['評分'], reverse=True)

    if st.button("🚀 啟動 AI 智能快篩", type="primary"):
        with st.spinner("掃描市場資金流向，精算買賣點..."):
            targets = auto_screener(strategic_pool)
            if targets:
                st.success(f"🎯 篩選完成！為您挑選出 {len(targets)} 檔最佳戰鬥目標：")
                for i, t in enumerate(targets):
                    ev_color = '#FF4B4B' if t['ev'] > 0 else '#00CC96'
                    crown_badge = "<span class='badge-gold'>👑 AI 首選</span> &nbsp;" if i < 2 else ""
                    
                    with st.container():
                        st.markdown(f"""
                        <div class="card">
                            <div style="margin-bottom: 10px;">
                                {crown_badge}<span class="big-font">{t['clean_sym']} {t['名稱']}</span> &nbsp; {t['status']}
                            </div>
                            <div>
                                <b>最新股價：</b> ${t['現價']:.2f} &nbsp;|&nbsp; 
                                <b>歷史短線勝率：</b> {t['win_rate']:.0f}%
                            </div>
                            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #ccc;">
                                🛒 <b>操作紀律：</b> 建議買入 <span class="highlight-blue">${t['buy_price']:.2f}</span> | 停利 <span class="highlight-red">${t['tp']:.2f}</span> | 月線停損 <span class="highlight-green">${t['停損']:.2f}</span><br>
                                💰 <b>2%風控配置：</b> 可打 <b>{t['建議股數']} 股</b> (預估淨利 ${t['net_profit']:,.0f} | 總稅費約 ${t['friction']:,.0f})<br>
                                📊 <b>AI 綜合戰鬥力：</b> <span style="color: #1E90FF; font-weight: bold;">{t['評分']:.1f} 分</span> (EV: <span style="color: {ev_color}; font-weight: bold;">${t['ev']:,.0f}</span>)
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.code(t['clean_sym'], language="text")
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.warning("📉 目前盤面無符合高勝率之標的，建議空手觀望。")

# =====================================================
# TAB 2: 個股診斷與消息面
# =====================================================
with tab2:
    col1, col2 = st.columns([3, 1])
    user_input = col1.text_input("輸入欲診斷股票代號", value="2330")
    btn = col2.button("執行深度診斷與查新聞", type="primary", use_container_width=True)

    if btn:
        parsed = smart_ticker_lookup(user_input)
        with st.spinner(f"正在分析 {parsed} ..."):
            hist = yf.download(parsed, period="6mo", progress=False)
            if not hist.empty:
                if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.droplevel(1)
                
                try: news_data = yf.Ticker(parsed).news
                except: news_data = []

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

                st.markdown("#### 📰 最新消息面追蹤")
                if news_data:
                    for n in news_data[:5]: 
                        try:
                            pub_time = datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d %H:%M')
                            st.markdown(f"""
                            <div class="news-box">
                                <span style="color: #888;">{pub_time} ({n.get('publisher', 'Yahoo')})</span><br>
                                <a href="{n['link']}" target="_blank" style="color: #FFF; text-decoration: none; font-weight: bold; font-size: 16px;">{n['title']}</a>
                            </div>
                            """, unsafe_allow_html=True)
                        except: pass
                else:
                    st.info("目前系統未爬取到近期重大新聞。")

                st.markdown("---")
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='日K'))
                fig.add_trace(go.Scatter(x=hist.index, y=hist['20MA'], name='20MA (月線)', line=dict(color='#9B59B6', width=2)))
                fig.update_layout(height=450, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("無法取得資料，請檢查股票代號。")

# =====================================================
# TAB 3: 交易紀錄與視覺化軌跡
# =====================================================
with tab3:
    st.markdown("### 🏆 實戰資產翻倍軌跡表")
    LOG_FILE = "trade_log.csv"
    if os.path.exists(LOG_FILE): 
        df = pd.read_csv(LOG_FILE)
    else: 
        df = pd.DataFrame({"日期":[datetime.now().strftime('%Y-%m-%d')], "標的":["3000元初始本金"], "單筆損益":[0]})

    total_pnl = df["單筆損益"].sum()
    current_capital = 3000 + total_pnl
    target = 500000
    
    c1, c2, c3 = st.columns(3)
    c1.metric("目前總資金", f"${current_capital:,.0f}")
    c2.metric("累計波段損益", f"${total_pnl:,.0f}", f"{(total_pnl/3000)*100:.1f}% 成長率")
    c3.metric("達成率", f"{(current_capital/target)*100:.2f} %")
    st.progress(min(current_capital / target, 1.0))

    st.markdown("#### 📝 填寫平倉紀錄 (系統將自動存檔繪圖)")
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    
    if not edited.equals(df):
        edited.to_csv(LOG_FILE, index=False)
        st.success("✅ 交易紀錄已儲存！請重新整理以更新圖表。")
    
    # 繪製真實交易軌跡
    if len(edited) > 0:
        edited['累計資金'] = 3000 + edited['單筆損益'].cumsum()
        fig_log = px.line(edited, x='日期', y='累計資金', markers=True, title="真實資產成長軌跡 (Equity Curve)")
        fig_log.update_layout(template="plotly_dark", yaxis_title="總資金 ($)", xaxis_title="日期")
        st.plotly_chart(fig_log, use_container_width=True)

# =====================================================
# TAB 4: 策略回測中心 (新增權益曲線圖)
# =====================================================
with tab4:
    st.markdown("### 🧪 突破策略高速回測引擎")
    st.caption("回測邏輯：均線多頭排列 + 突破 20 日新高進場 ➔ 跌破 20MA 月線出場 (回測期間：近 2 年)")
    
    col_t1, col_t2 = st.columns([3, 1])
    ticker_bt = col_t1.text_input("輸入欲回測代號", value="2330", key="bt_ticker")
    if col_t2.button("🚀 執行回測", use_container_width=True):
        parsed = smart_ticker_lookup(ticker_bt)
        with st.spinner("極速模擬近兩年交易中..."):
            hist = yf.download(parsed, period="2y", progress=False)
            if not hist.empty:
                if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.droplevel(1)
                hist = calculate_indicators(hist)
                
                results = []
                bt_dates = []
                bt_equity = []
                position = 0
                entry_price = 0
                cumulative_points = 0 # 累計賺取的價差

                for i in range(50, len(hist)):
                    today = hist.iloc[i]
                    date_str = hist.index[i].strftime('%Y-%m-%d')
                    recent_high = today['Recent_High20'] 

                    if position == 0:
                        if (today['Close'] > recent_high and today['5MA'] > today['10MA'] > today['20MA'] and 50 < today['RSI'] < 75):
                            position = 1
                            entry_price = today['Close']
                    else:
                        stop = today['20MA'] * 0.99
                        if today['Close'] < stop:
                            profit = today['Close'] - entry_price
                            results.append(profit)
                            cumulative_points += profit
                            bt_dates.append(date_str)
                            bt_equity.append(cumulative_points)
                            position = 0

                if results:
                    win = len([r for r in results if r > 0])
                    win_rate = win / len(results) * 100
                    avg_profit = sum(results) / len(results)

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("歷史交易次數", f"{len(results)} 次")
                    c2.metric("策略勝率", f"{win_rate:.1f}%")
                    c3.metric("單次平均創造價差", f"${avg_profit:.2f}")
                    c4.metric("總累計價差", f"${cumulative_points:.2f}")
                    
                    # 繪製回測權益曲線 (Equity Curve)
                    st.markdown("#### 📈 策略回測累積獲利軌跡")
                    df_bt = pd.DataFrame({"日期": bt_dates, "累計獲利價差": bt_equity})
                    fig_bt = px.line(df_bt, x='日期', y='累計獲利價差', markers=True)
                    fig_bt.update_layout(template="plotly_dark", yaxis_title="累計獲利 (點/元)")
                    st.plotly_chart(fig_bt, use_container_width=True)
                else:
                    st.warning("此區間內該股票未產生符合「20日新高突破」的交易訊號，可能長期處於空頭或震盪。")
            else:
                st.error("無法取得回測數據。")
