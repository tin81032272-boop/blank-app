import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime
import pytz
import os
import re

st.set_page_config(page_title="當沖指揮中心 Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .big-font { font-size:22px !important; font-weight: bold; color: #1E90FF; }
    .report-card { background-color: #1E1E1E; color: white; padding: 20px; border-radius: 12px; border-top: 5px solid #FF4B4B; margin-top: 15px; }
    .metric-box { background-color: #2b2b2b; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #444;}
    .highlight-red { color: #FF4B4B; font-weight: bold; }
    .highlight-green { color: #00CC96; font-weight: bold; }
    .highlight-vwap { color: #9B59B6; font-weight: bold; }
    .card { background-color: #f8f9fa; color: #333; padding: 18px; border-radius: 12px; border-left: 6px solid #1E90FF; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);}
    .badge-red { background-color: #FF4B4B; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-green { background-color: #00CC96; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-gray { background-color: #555555; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 置頂控制區
# =====================================================
colA, colB = st.columns([3, 1])
with colA:
    st.title("⚡ 終極當沖指揮中心 (Pro Max)")
with colB:
    st.write("") 
    if st.button("🔄 盤中一鍵極速刷新", type="primary", use_container_width=True):
        st.cache_data.clear()

tw_tz = pytz.timezone('Asia/Taipei')
now = datetime.now(tw_tz)
is_open = now.replace(hour=9, minute=0, second=0) <= now <= now.replace(hour=13, minute=30, second=0) and now.weekday() < 5
status_msg = "🟢 盤中激戰中" if is_open else "🔴 市場休息"
st.caption(f"{status_msg} | 系統時間：{now.strftime('%Y-%m-%d %H:%M:%S')} | 核心策略：VWAP 均價線 + 爆量動能")

if is_open and now.hour == 9 and now.minute < 15:
    st.warning("⚠️ **開盤大亂鬥警告**：09:00~09:15 API 可能有延遲，請務必搭配券商軟體確認即時現價與量能！")

# =====================================================
# 當沖熱門高週轉率股池
# =====================================================
daytrade_pool = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "3231.TW": "緯創", "2382.TW": "廣達", "2356.TW": "英業達",
    "1519.TW": "華城", "1513.TW": "中興電", "1514.TW": "亞力", "1504.TW": "東元", "2371.TW": "大同",
    "2603.TW": "長榮", "2609.TW": "陽明", "2615.TW": "萬海", "2618.TW": "長榮航", "2610.TW": "華航",
    "3324.TW": "雙鴻", "3017.TW": "奇鋐", "2421.TW": "建準", "3034.TW": "聯詠", "2379.TW": "瑞昱",
    "3661.TW": "世芯-KY", "3443.TW": "創意", "3450.TW": "聯鈞", "4979.TW": "華星光", "3081.TWO": "聯亞",
    "2365.TW": "昆盈", "2359.TW": "所羅門", "4562.TWO": "穎漢", "8033.TWO": "雷虎", "2409.TW": "友達"
}

def smart_ticker_lookup(user_input):
    user_input = str(user_input).strip().upper()
    if not user_input: return None
    if ".TW" in user_input or ".TWO" in user_input: return user_input
    for sym, name in daytrade_pool.items():
        if user_input in name.upper() or user_input in sym.upper(): return sym
    if user_input.isdigit(): return user_input + ".TW"
    return user_input

tab1, tab2, tab3 = st.tabs(["🎯 盤中爆量雷達", "📈 5分K VWAP 戰術圖表", "📊 當沖損益記帳本"])

# =====================================================
# TAB 1: 盤中爆量雷達
# =====================================================
with tab1:
    st.markdown("### ⚡ 當沖狙擊目標過濾")
    
    c1, c2 = st.columns(2)
    capital_limit = c1.number_input("當沖額度上限 (元)", value=500000, step=100000)
    rvol_limit = c2.slider("爆量倍數要求 (RVOL)", 0.5, 5.0, value=1.2, step=0.1, help="盤中量能與過去平均的倍數比")
    
    @st.cache_data(ttl=180) # 當沖需要快取時間短一點 (3分鐘)
    def scan_daytrade_candidates(pool, capital, rvol_req):
        results = []
        for sym, desc in pool.items():
            try:
                # 抓取日線算昨日關鍵價
                s = yf.Ticker(sym)
                hist_1d = s.history(period="10d")
                if len(hist_1d) < 2: continue
                
                yest = hist_1d.iloc[-2]
                pivot = (yest['High'] + yest['Low'] + yest['Close']) / 3
                r1 = (2 * pivot) - yest['Low']  # 今日壓力
                s1 = (2 * pivot) - yest['High'] # 今日支撐
                
                # 抓取今日即時數據
                today = hist_1d.iloc[-1]
                curr_price = today['Close']
                
                # 計算是否買得起整張 (當沖建議打整張)
                cost_per_lot = curr_price * 1000
                affordable_lots = int(capital // cost_per_lot)
                if affordable_lots < 1: continue
                
                # 爆量計算 (粗估)
                avg_vol_5d = hist_1d['Volume'].rolling(5).mean().iloc[-2]
                rvol = today['Volume'] / avg_vol_5d if avg_vol_5d > 0 else 1
                if rvol < rvol_req: continue 
                
                # 計算 ATR (用於當沖停損)
                hist_1d['TR'] = hist_1d['High'] - hist_1d['Low']
                atr = hist_1d['TR'].rolling(14).mean().iloc[-1]
                
                # 當沖利潤精算 (手續費 2.8折，當沖交易稅減半 0.15%)
                est_gross_profit = affordable_lots * 1000 * (atr * 0.5) # 當沖只抓半個 ATR 波動
                fee_rate = 0.001425 * 0.28
                friction = affordable_lots * ((curr_price * 1000 * fee_rate * 2) + (curr_price * 1000 * 0.0015))
                net_profit = est_gross_profit - friction
                if net_profit <= 0: continue
                
                # 強弱判斷
                if curr_price > r1: status = "<span class='badge-red'>突破壓力 ⬆</span>"
                elif curr_price < s1: status = "<span class='badge-green'>跌破支撐 ⬇</span>"
                else: status = "<span class='badge-gray'>區間震盪 ↔</span>"
                
                clean_sym = sym.replace('.TW', '').replace('.TWO', '')
                
                results.append({
                    "symbol": sym, "clean_sym": clean_sym, "desc": desc, "price": curr_price,
                    "r1": r1, "s1": s1, "rvol": rvol, "lots": affordable_lots, 
                    "net_profit": net_profit, "friction": friction, "status": status
                })
            except: pass
        return sorted(results, key=lambda x: x['rvol'], reverse=True)

    if st.button("🚀 啟動盤中爆量雷達", type="primary", use_container_width=True):
        with st.spinner("掃描當沖熱門股中..."):
            targets = scan_daytrade_candidates(daytrade_pool, capital_limit, rvol_limit)
            if targets:
                st.success(f"🎯 鎖定 **{len(targets)}** 檔當沖動能標的：")
                for t in targets:
                    with st.container():
                        st.markdown(f"""
                        <div class="card">
                            <div style="margin-bottom: 10px;">
                                <span class="big-font">{t['clean_sym']} {t['desc']}</span> &nbsp; {t['status']}
                            </div>
                            <div>
                                <b>即時股價：</b> ${t['price']:.2f} &nbsp;|&nbsp; 
                                <b>爆量倍數：</b> <span style="color:#FF4B4B;">{t['rvol']:.1f}x</span>
                            </div>
                            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #ccc;">
                                🎯 <b>關鍵點位：</b> 上方壓力 <span class="highlight-red">${t['r1']:.2f}</span> | 下方支撐 <span class="highlight-green">${t['s1']:.2f}</span><br>
                                💰 <b>當沖配置：</b> 可打 <b>{t['lots']} 張</b> (估計淨利 ${t['net_profit']:,.0f} | 交易稅費 ${t['friction']:,.0f})
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.caption("👇 點擊右側圖示複製代號，準備切換券商下單")
                        st.code(t['clean_sym'], language="text")
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.warning("📉 目前無符合條件之標的。可能剛開盤量能未出，或盤勢過於沉悶。可稍後點擊【一鍵極速刷新】。")

# =====================================================
# TAB 2: 5分K VWAP 戰術圖表
# =====================================================
with tab2:
    st.markdown("### 📈 專業當沖雙視窗 (5分K + VWAP + MACD)")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    quick_select_list = ["--- 自行輸入 ---"] + [f"{k.replace('.TW','')} {v}" for k, v in daytrade_pool.items()]
    quick_choice = col1.selectbox("📋 快速選擇熱門股", quick_select_list)
    default_input = quick_choice.split(" ")[0] if quick_choice != "--- 自行輸入 ---" else "2330"
    user_input = col2.text_input("✍️ 或自行輸入代號", value=default_input)
    btn = col3.button("🧠 載入即時 5 分 K", type="primary", use_container_width=True)

    if btn:
        parsed = smart_ticker_lookup(user_input)
        with st.spinner(f"正在抓取 {parsed} 的 5分K 與計算 VWAP..."):
            try:
                s = yf.Ticker(parsed)
                # 當沖抓最近 2 天的 5 分 K
                hist_5m = s.history(period="2d", interval="5m")
                
                if not hist_5m.empty:
                    # 分離出「今天」的數據來獨立計算 VWAP
                    today_date = hist_5m.index[-1].date()
                    today_data = hist_5m[hist_5m.index.date == today_date].copy()
                    
                    if not today_data.empty:
                        # 1. 計算今日 VWAP (當沖靈魂)
                        today_data['Typical'] = (today_data['High'] + today_data['Low'] + today_data['Close']) / 3
                        today_data['VWAP'] = (today_data['Typical'] * today_data['Volume']).cumsum() / today_data['Volume'].cumsum()
                        
                        # 2. 計算 5分 K 的 MACD
                        exp1 = today_data['Close'].ewm(span=12, adjust=False).mean()
                        exp2 = today_data['Close'].ewm(span=26, adjust=False).mean()
                        today_data['MACD'] = exp1 - exp2
                        today_data['Signal'] = today_data['MACD'].ewm(span=9, adjust=False).mean()
                        today_data['Hist'] = today_data['MACD'] - today_data['Signal']
                        
                        curr_price = today_data['Close'].iloc[-1]
                        last_vwap = today_data['VWAP'].iloc[-1]
                        
                        # 當沖戰略判定
                        if curr_price > last_vwap:
                            trend_desc = "🟢 大戶偏多 (股價在 VWAP 之上)"
                            action = "建議【順勢做多】，以 VWAP 作為短線停損防守線。"
                            box_color = "#00CC96"
                        elif curr_price < last_vwap:
                            trend_desc = "🔴 大戶偏空 (股價在 VWAP 之下)"
                            action = "建議【順勢做空】或【空手觀望】，若反彈突破 VWAP 再翻多。"
                            box_color = "#FF4B4B"
                        else:
                            trend_desc = "🟡 多空交戰 (黏著 VWAP)"
                            action = "盤整中，等待帶量脫離 VWAP 表態。"
                            box_color = "#FFD700"

                        stock_name = daytrade_pool.get(parsed, parsed.replace('.TW',''))
                        
                        st.markdown(f"""
                        <div class="report-card" style="border-top: 5px solid {box_color};">
                            <h3 style="margin-top:0;">{stock_name} 盤中 VWAP 戰情</h3>
                            <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                                <div class="metric-box" style="flex: 1;"><b>即時現價</b><br><span style="font-size:20px;">${curr_price:.2f}</span></div>
                                <div class="metric-box" style="flex: 1;"><b>VWAP 均價線</b><br><span class="highlight-vwap" style="font-size:20px;">${last_vwap:.2f}</span></div>
                                <div class="metric-box" style="flex: 1;"><b>距離 VWAP</b><br><span style="color:{box_color}; font-size:20px;">{((curr_price-last_vwap)/last_vwap)*100:.2f}%</span></div>
                            </div>
                            <div style="background-color: #2b2b2b; padding: 10px; border-radius: 5px;">
                                <b>戰術指示：</b><span style="color: {box_color};">{trend_desc}</span> ➔ {action}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # 繪製專業當沖雙層圖表
                        st.markdown("#### 📊 5分K 狙擊圖表")
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
                        
                        # 主圖：5分K 與 VWAP
                        fig.add_trace(go.Candlestick(x=today_data.index, open=today_data['Open'], high=today_data['High'], low=today_data['Low'], close=today_data['Close'], name='5分K'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=today_data.index, y=today_data['VWAP'], name='VWAP (主力成本)', line=dict(color='#9B59B6', width=2)), row=1, col=1)
                        
                        # 副圖：MACD
                        macd_colors = ['#FF4B4B' if val > 0 else '#00CC96' for val in today_data['Hist']]
                        fig.add_trace(go.Bar(x=today_data.index, y=today_data['Hist'], marker_color=macd_colors, name='MACD柱'), row=2, col=1)
                        fig.add_trace(go.Scatter(x=today_data.index, y=today_data['MACD'], line=dict(color='#1E90FF', width=1), name='MACD'), row=2, col=1)
                        fig.add_trace(go.Scatter(x=today_data.index, y=today_data['Signal'], line=dict(color='#FFD700', width=1), name='Signal'), row=2, col=1)

                        fig.update_layout(height=600, margin=dict(l=0,r=0,t=10,b=0), xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False, template="plotly_dark", hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("今日尚無交易數據。")
            except Exception as e:
                st.error("無法取得即時資料，可能是網路延遲或代號錯誤。")

# =====================================================
# TAB 3: 當沖損益記帳本
# =====================================================
with tab3:
    st.markdown("### 🏆 每日當沖實戰損益紀錄")
    LOG_FILE = "daytrade_log.csv"
    if os.path.exists(LOG_FILE): df = pd.read_csv(LOG_FILE)
    else: df = pd.DataFrame({"日期":[datetime.now().strftime('%Y-%m-%d')], "操作":["多/空"], "標的":["2330"], "當沖淨利(NTD)":[0]})

    total_pnl = df["當沖淨利(NTD)"].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("當沖累計總淨利", f"NT$ {total_pnl:,.0f}")
    c2.metric("交易筆數", f"{len(df)-1} 筆") # 扣掉初始紀錄

    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if not edited.equals(df):
        edited.to_csv(LOG_FILE, index=False)
        st.success("✅ 當沖紀錄已儲存！")
    
    if len(edited) > 1:
        edited['累計獲利'] = edited['當沖淨利(NTD)'].cumsum()
        fig_log = px.bar(edited, x='日期', y='當沖淨利(NTD)', title="每日當沖損益柱狀圖", color='當沖淨利(NTD)', color_continuous_scale=['#00CC96', '#FF4B4B'])
        fig_log.update_layout(template="plotly_dark", yaxis_title="淨利 (NT$)")
        st.plotly_chart(fig_log, use_container_width=True)
