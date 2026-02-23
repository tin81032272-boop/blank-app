import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# --- 初始化參數 ---
if 'win_rate' not in st.session_state: st.session_state.win_rate = 60
if 'rvol' not in st.session_state: st.session_state.rvol = 1.2

def relax_params():
    st.session_state.win_rate = 50
    st.session_state.rvol = 0.8

st.set_page_config(page_title="Pro 當沖指揮中心", page_icon="⚡", layout="centered")

st.markdown("""
<style>
    .badge-red { background-color: #FF4B4B; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-green { background-color: #00CC96; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-gray { background-color: #555555; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .highlight-red { color: #FF4B4B; font-weight: bold; font-size: 16px; }
    .highlight-green { color: #00CC96; font-weight: bold; font-size: 16px; }
    .metric-box { background-color: #1E1E1E; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #333;}
</style>
""", unsafe_allow_html=True)

# --- 頂部狀態列與全局刷新 ---
colA, colB = st.columns([2, 1])
with colA:
    st.title("⚡ Pro 當沖指揮中心")
with colB:
    st.write("") # 排版微調
    if st.button("🔄 一鍵全局刷新", use_container_width=True, type="primary"):
        st.cache_data.clear()

tw_tz = pytz.timezone('Asia/Taipei')
now = datetime.now(tw_tz)
is_open = now.replace(hour=9, minute=0, second=0) <= now <= now.replace(hour=13, minute=30, second=0) and now.weekday() < 5
status_msg = "🟢 盤中交易中" if is_open else "🔴 市場已收盤"
st.caption(f"{status_msg} | 系統時間：{now.strftime('%Y-%m-%d %H:%M:%S')}")

with st.expander("⚙️ 戰略參數設定 (點擊展開)", expanded=False):
    c1, c2 = st.columns(2)
    capital_limit = c1.number_input("資金上限 (元)", value=500000, step=50000)
    min_win_rate = c2.slider("要求勝率 (%)", 30, 100, step=5, key="win_rate")
    c3, c4 = st.columns(2)
    max_price = c3.number_input("股價上限 (元)", value=250.0, step=10.0)
    min_rvol = c4.slider("爆量倍數 (RVOL)", 0.5, 5.0, step=0.1, key="rvol")
    fee_discount = 2.8

st.markdown("---")

strategic_pool = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2382.TW": "廣達", "3231.TW": "緯創",
    "2376.TW": "技嘉", "2356.TW": "英業達", "2324.TW": "仁寶", "2353.TW": "宏碁", "2357.TW": "華碩",
    "1519.TW": "華城", "1513.TW": "中興電", "1504.TW": "東元", "1514.TW": "亞力", "2371.TW": "大同",
    "1609.TW": "大亞", "1605.TW": "華新", "1608.TW": "華榮", "1618.TW": "合機", "2009.TW": "第一銅",
    "2603.TW": "長榮", "2609.TW": "陽明", "2615.TW": "萬海", "2618.TW": "長榮航", "2610.TW": "華航",
    "2634.TW": "漢翔", "8033.TWO": "雷虎", "2314.TW": "台揚", "3481.TW": "群創", "2409.TW": "友達",
    "2365.TW": "昆盈", "6188.TWO": "廣明", "4562.TWO": "穎漢", "2359.TW": "所羅門", "3324.TW": "雙鴻",
    "3017.TW": "奇鋐", "2421.TW": "建準", "3034.TW": "聯詠", "2379.TW": "瑞昱", "3443.TW": "創意",
    "3661.TW": "世芯-KY", "3081.TWO": "聯亞", "4979.TW": "華星光", "3450.TW": "聯鈞", "2344.TW": "華邦電"
}

def smart_ticker_lookup(user_input):
    user_input = str(user_input).strip()
    if not user_input: return None
    if ".TW" in user_input.upper(): return user_input.upper()
    for sym, name in strategic_pool.items():
        if user_input == name or user_input in sym: return sym
    return user_input + ".TW"

tab1, tab2 = st.tabs(["🎯 戰情雷達 (過濾選股)", "📈 全景戰術圖表 (買點與指標)"])

# ==========================================
# 分頁 1：戰情雷達
# ==========================================
with tab1:
    @st.cache_data(ttl=300)
    def scan_pro_candidates(pool, capital, required_win_rate, discount, rvol_req, price_limit):
        results = []
        for sym, desc in pool.items():
            try:
                stock = yf.Ticker(sym)
                hist = stock.history(period="1mo")
                if len(hist) < 15: continue
                
                win_days = (hist['High'] - hist['Open']) / hist['Open'] >= 0.01 
                win_rate = (win_days.sum() / len(win_days)) * 100
                if win_rate < required_win_rate: continue
                
                today = hist.iloc[-1]
                curr_price = today['Close']
                if curr_price > price_limit: continue
                
                cost_per_lot = curr_price * 1000
                affordable_lots = int(capital // cost_per_lot)
                if affordable_lots < 1: continue
                
                avg_vol_10d = hist['Volume'].rolling(10).mean().iloc[-2]
                rvol = today['Volume'] / avg_vol_10d if avg_vol_10d > 0 else 1
                if rvol < rvol_req: continue 
                
                hist['TR'] = hist['High'] - hist['Low']
                atr = hist['TR'].rolling(14).mean().iloc[-1]
                
                sl = curr_price - (atr * 0.5) 
                tp = curr_price + (atr * 1.0) 
                
                est_gross_profit = affordable_lots * 1000 * (atr * 1.0)
                fee_rate = 0.001425 * (discount / 10)
                friction = affordable_lots * ((curr_price * 1000 * fee_rate * 2) + (curr_price * 1000 * 0.0015))
                net_profit = est_gross_profit - friction
                if net_profit <= 0: continue
                
                ev = (win_rate/100 * est_gross_profit) - ((1 - win_rate/100) * (affordable_lots * 1000 * atr * 0.5))
                status_badge = "<span class='badge-red'>今日強勢 ⬆</span>" if today['Close'] > hist.iloc[-2]['Close'] else "<span class='badge-green'>今日弱勢 ⬇</span>"
                clean_sym = sym.replace('.TW', '').replace('.TWO', '')
                
                results.append({
                    "symbol": sym, "clean_sym": clean_sym, "desc": desc, "price": curr_price,
                    "win_rate": win_rate, "rvol": rvol, "atr": atr, "lots": affordable_lots, 
                    "net_profit": net_profit, "sl": sl, "tp": tp, "status": status_badge, "ev": ev
                })
            except: pass
        return sorted(results, key=lambda x: x['rvol'], reverse=True)

    with st.spinner("⚡ 啟動量化引擎，過濾百大股池..."):
        targets = scan_pro_candidates(strategic_pool, capital_limit, st.session_state.win_rate, fee_discount, st.session_state.rvol, max_price)
        
    if targets:
        st.success(f"🎯 鎖定 **{len(targets)}** 檔狙擊目標：")
        for t in targets:
            ev_color = '#FF4B4B' if t['ev'] > 0 else '#00CC96'
            with st.container():
                st.markdown(f"### {t['desc']} {t['status']}", unsafe_allow_html=True)
                colA, colB = st.columns([3, 1])
                with colA:
                    st.write(f"**股價:** ${t['price']:.2f} | **爆量:** {t['rvol']:.1f}x | **勝率:** {t['win_rate']:.0f}%")
                    st.write(f"停利 <span class='highlight-red'>${t['tp']:.2f}</span> | 停損 <span class='highlight-green'>${t['sl']:.2f}</span>", unsafe_allow_html=True)
                with colB:
                    st.code(t['clean_sym'], language="text")
                st.markdown("---")
    else:
        st.warning("📉 目前無符合條件之標的。")
        st.button("⚡ 一鍵放寬策略", on_click=relax_params, type="primary")

# ==========================================
# 分頁 2：全景戰術圖表 & 即時指標
# ==========================================
with tab2:
    user_search = st.text_input("🔍 快速分析 (輸入代號或名稱，如：2330 或 台積電)", placeholder="支援中文搜尋...")
    
    # 圖表圖層開關 (直覺化操作)
    st.markdown("##### 🎛️ 圖表顯示控制")
    t1, t2, t3 = st.columns(3)
    show_vwap = t1.toggle("顯示 VWAP", value=True)
    show_bb = t2.toggle("顯示布林通道", value=False)
    show_pivot = t3.toggle("顯示壓力支撐", value=False)

    chart_list = []
    if user_search:
        parsed_ticker = smart_ticker_lookup(user_search)
        if parsed_ticker: chart_list.append({"symbol": parsed_ticker, "desc": user_search})
    elif targets:
        chart_list = targets
        st.info(f"👉 自動展開今日 **{len(targets)}** 檔精選標的之 5 分 K 線：")

    if chart_list:
        for item in chart_list:
            sym = item['symbol']
            try:
                s = yf.Ticker(sym)
                hist_5m = s.history(period="2d", interval="5m") # 抓2天確保指標算得出來
                hist_1d = s.history(period="5d", interval="1d")
                
                if not hist_5m.empty and len(hist_1d) >= 2:
                    # --- 指標計算區 ---
                    # 1. Pivot Points
                    yest = hist_1d.iloc[-2]
                    pivot = (yest['High'] + yest['Low'] + yest['Close']) / 3
                    r1 = (2 * pivot) - yest['Low']
                    s1 = (2 * pivot) - yest['High']
                    
                    # 取出今天的資料來畫圖
                    today_date = hist_5m.index[-1].date()
                    today_data = hist_5m[hist_5m.index.date == today_date].copy()
                    if today_data.empty: continue
                    
                    curr_price = today_data['Close'].iloc[-1]
                    
                    # 2. VWAP (僅算今日)
                    today_data['Typical'] = (today_data['High'] + today_data['Low'] + today_data['Close']) / 3
                    today_data['VWAP'] = (today_data['Typical'] * today_data['Volume']).cumsum() / today_data['Volume'].cumsum()
                    last_vwap = today_data['VWAP'].iloc[-1]
                    
                    # 3. RSI (14T)
                    delta = hist_5m['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    hist_5m['RSI'] = 100 - (100 / (1 + rs))
                    last_rsi = hist_5m['RSI'].iloc[-1]
                    
                    # 4. MACD (12, 26, 9)
                    exp1 = hist_5m['Close'].ewm(span=12, adjust=False).mean()
                    exp2 = hist_5m['Close'].ewm(span=26, adjust=False).mean()
                    hist_5m['MACD'] = exp1 - exp2
                    hist_5m['Signal'] = hist_5m['MACD'].ewm(span=9, adjust=False).mean()
                    last_macd = hist_5m['MACD'].iloc[-1]
                    last_signal = hist_5m['Signal'].iloc[-1]
                    
                    # 5. Bollinger Bands (20T, 2SD)
                    hist_5m['MA20'] = hist_5m['Close'].rolling(window=20).mean()
                    hist_5m['BB_std'] = hist_5m['Close'].rolling(window=20).std()
                    hist_5m['BB_upper'] = hist_5m['MA20'] + (hist_5m['BB_std'] * 2)
                    hist_5m['BB_lower'] = hist_5m['MA20'] - (hist_5m['BB_std'] * 2)
                    
                    # 對齊今日數據
                    today_data['BB_upper'] = hist_5m['BB_upper'].loc[today_data.index]
                    today_data['BB_lower'] = hist_5m['BB_lower'].loc[today_data.index]

                    # --- 繪製圖表 ---
                    st.markdown(f"#### 📌 {item.get('desc', sym)} ({sym.replace('.TW','')})")
                    
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=today_data.index, open=today_data['Open'], high=today_data['High'], low=today_data['Low'], close=today_data['Close'], 
                        name='5分K', increasing_line_color='#FF4B4B', increasing_fillcolor='#FF4B4B', decreasing_line_color='#00CC96', decreasing_fillcolor='#00CC96'  
                    ))
                    
                    if show_vwap:
                        fig.add_trace(go.Scatter(x=today_data.index, y=today_data['VWAP'], mode='lines', name='VWAP', line=dict(color='#9B59B6', width=2)))
                    
                    if show_bb:
                        fig.add_trace(go.Scatter(x=today_data.index, y=today_data['BB_upper'], mode='lines', line=dict(color='rgba(173, 216, 230, 0.4)', width=1), name='布林上軌'))
                        fig.add_trace(go.Scatter(x=today_data.index, y=today_data['BB_lower'], mode='lines', line=dict(color='rgba(173, 216, 230, 0.4)', width=1), fill='tonexty', fillcolor='rgba(173, 216, 230, 0.1)', name='布林下軌'))
                    
                    if show_pivot:
                        fig.add_hline(y=r1, line_dash="dash", line_color="#FF4B4B", annotation_text="壓力(R1)")
                        fig.add_hline(y=s1, line_dash="dash", line_color="#00CC96", annotation_text="支撐(S1)")
                    
                    fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # --- 動能儀表板 (視覺化文字判定) ---
                    m1, m2, m3 = st.columns(3)
                    
                    # VWAP 判定
                    if curr_price > last_vwap: vwap_status = "<span class='badge-red'>多方控盤</span>"
                    elif curr_price < last_vwap: vwap_status = "<span class='badge-green'>空方壓制</span>"
                    else: vwap_status = "<span class='badge-gray'>多空交戰</span>"
                    m1.markdown(f"<div class='metric-box'><b>VWAP 趨勢</b><br>{vwap_status}</div>", unsafe_allow_html=True)
                    
                    # RSI 判定
                    if last_rsi > 70: rsi_status = "<span class='badge-red'>🔥過熱超買</span>"
                    elif last_rsi < 30: rsi_status = "<span class='badge-green'>❄️超跌超賣</span>"
                    else: rsi_status = "<span class='badge-gray'>區間震盪</span>"
                    m2.markdown(f"<div class='metric-box'><b>RSI ({last_rsi:.1f})</b><br>{rsi_status}</div>", unsafe_allow_html=True)
                    
                    # MACD 判定
                    if last_macd > last_signal and last_macd > 0: macd_status = "<span class='badge-red'>🚀 多頭發散</span>"
                    elif last_macd < last_signal and last_macd < 0: macd_status = "<span class='badge-green'>📉 空頭發散</span>"
                    elif last_macd > last_signal: macd_status = "<span class='badge-red'>黃金交叉</span>"
                    else: macd_status = "<span class='badge-green'>死亡交叉</span>"
                    m3.markdown(f"<div class='metric-box'><b>MACD 動能</b><br>{macd_status}</div>", unsafe_allow_html=True)

                    st.markdown("<br><hr style='border:1px dashed #444;'><br>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"無法取得 {sym} 的圖表資料。")
