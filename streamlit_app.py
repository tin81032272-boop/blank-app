import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# --- 網頁與視覺主題設定 ---
st.set_page_config(page_title="Pro 當沖指揮中心", page_icon="⚡", layout="centered")

# 自訂 CSS 讓介面更像專業 APP
st.markdown("""
<style>
    .big-font { font-size:20px !important; font-weight: bold; color: #1E90FF; }
    .badge-red { background-color: #FF4B4B; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-green { background-color: #00CC96; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-gray { background-color: #555555; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .card { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1E90FF; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Pro 當沖指揮中心")

# --- 台灣時間與市場狀態燈 ---
tw_tz = pytz.timezone('Asia/Taipei')
now = datetime.now(tw_tz)
current_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

# 判斷是否為盤中 (09:00 - 13:30)
market_open = now.replace(hour=9, minute=0, second=0)
market_close = now.replace(hour=13, minute=30, second=0)
is_open = market_open <= now <= market_close and now.weekday() < 5

if is_open:
    st.markdown(f"### 🟢 **盤中交易中** | {current_time_str}")
else:
    st.markdown(f"### 🔴 **市場已收盤/休市** | {current_time_str}")

# --- 參數設定區 (收合式設計，畫面更乾淨) ---
with st.expander("⚙️ 打擊區參數設定 (點擊展開/收合)", expanded=False):
    st.markdown("💡 *調整參數後，系統會即時重新掃描*")
    col1, col2 = st.columns(2)
    capital_limit = col1.number_input("總資金上限 (元)", value=500000, step=50000)
    min_win_rate = col2.slider("要求勝率 (%)", min_value=50, max_value=100, value=80, step=5)
    
    col3, col4 = st.columns(2)
    max_price = col3.number_input("單張股價上限 (元)", value=150.0, step=10.0)
    min_rvol = col4.slider("爆量倍數 (RVOL)", min_value=0.5, max_value=5.0, value=1.2, step=0.1)
    fee_discount = st.number_input("券商折數", value=2.8, step=0.1)

st.markdown("---")

# --- 雙分頁設計 ---
tab1, tab2 = st.tabs(["🎯 戰情雷達 (主力動向)", "📈 戰術圖表 (台股專屬 K 線)"])

# ==========================================
# 分頁 1：視覺化戰情雷達
# ==========================================
with tab1:
    # 戰略池：航太、機器人、重電、稀有金屬
    strategic_pool = {
        "2634.TW": "漢翔", "2314.TW": "台揚", "8033.TWO": "雷虎", 
        "2009.TW": "第一銅", "1605.TW": "華新", "8390.TWO": "金益鼎",
        "2365.TW": "昆盈", "4562.TWO": "穎漢", "6188.TWO": "廣明", 
        "2371.TW": "大同", "1608.TW": "華榮", "1609.TW": "大亞", "1618.TW": "合機",
        "1504.TW": "東元", "1513.TW": "中興電", "1519.TW": "華城"
    }

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
                
                # 判斷今日強弱 (紅綠標籤)
                status_badge = "<span class='badge-red'>今日強勢 ⬆</span>" if today['Close'] > hist.iloc[-2]['Close'] else "<span class='badge-green'>今日弱勢 ⬇</span>"
                
                results.append({
                    "symbol": sym, "desc": desc, "price": curr_price,
                    "win_rate": win_rate, "rvol": rvol, "atr": atr,
                    "lots": affordable_lots, "net_profit": net_profit,
                    "sl": sl, "tp": tp, "status": status_badge
                })
            except Exception:
                pass
        return sorted(results, key=lambda x: x['rvol'], reverse=True)

    with st.spinner("⚡ 啟動量化引擎，掃描市場資金流向..."):
        targets = scan_pro_candidates(strategic_pool, capital_limit, min_win_rate, fee_discount, min_rvol, max_price)
        
    if targets:
        st.success(f"🎯 鎖定 **{len(targets)}** 檔狙擊目標：")
        for t in targets:
            # 使用精美的 HTML 卡片排版
            st.markdown(f"""
            <div class="card">
                <div><span class="big-font">{t['symbol']} {t['desc']}</span> &nbsp; {t['status']}</div>
                <div style="margin-top: 8px;">
                    <b>最新股價：</b> ${t['price']:.2f} &nbsp;|&nbsp; 
                    <b>爆量倍數：</b> {t['rvol']:.1f}x &nbsp;|&nbsp; 
                    <b>勝率：</b> {t['win_rate']:.0f}%
                </div>
                <div style="margin-top: 5px; color: #555;">
                    🛒 <b>操作紀律：</b> 停利目標 <span style="color:#FF4B4B;">${t['tp']:.2f}</span> / 停損防守 <span style="color:#00CC96;">${t['sl']:.2f}</span><br>
                    💰 <b>配置建議：</b> 資金可打 {t['lots']} 張 (預估淨利 ${t['net_profit']:,.0f})
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📉 目前無符合條件之標的。若想放寬標準，請點擊上方『參數設定區』調降勝率或爆量倍數。")

# ==========================================
# 分頁 2：台股專屬紅綠 K 線 + 壓力支撐線
# ==========================================
with tab2:
    st.markdown("### 📊 戰略圖表 (VWAP + Pivot 支撐壓力)")
    ticker = st.text_input("輸入欲觀察的代號 (如 1609.TW)", value="1609.TW")
    
    if st.button("🔄 刷新即時圖表"):
        st.cache_data.clear()
        
    if ticker:
        try:
            s = yf.Ticker(ticker)
            # 抓取今天 5 分K 與 近期日K (用來算壓力支撐)
            hist_5m = s.history(period="1d", interval="5m") 
            hist_1d = s.history(period="5d", interval="1d")
            
            if not hist_5m.empty and len(hist_1d) >= 2:
                curr_price = hist_5m['Close'].iloc[-1]
                
                # --- 計算 Pivot Points (利用昨天的高低收) ---
                yest = hist_1d.iloc[-2]
                pivot = (yest['High'] + yest['Low'] + yest['Close']) / 3
                r1 = (2 * pivot) - yest['Low']   # 壓力線 1
                s1 = (2 * pivot) - yest['High']  # 支撐線 1
                
                # --- 計算 VWAP ---
                hist_5m['Typical_Price'] = (hist_5m['High'] + hist_5m['Low'] + hist_5m['Close']) / 3
                hist_5m['VWAP'] = (hist_5m['Typical_Price'] * hist_5m['Volume']).cumsum() / hist_5m['Volume'].cumsum()
                
                # --- 繪製專業圖表 ---
                fig = go.Figure()
                
                # 台股專屬 K 線顏色 (紅漲、綠跌)
                fig.add_trace(go.Candlestick(
                    x=hist_5m.index, open=hist_5m['Open'], high=hist_5m['High'], low=hist_5m['Low'], close=hist_5m['Close'], 
                    name='5分K',
                    increasing_line_color='#FF4B4B', increasing_fillcolor='#FF4B4B', # 上漲為紅
                    decreasing_line_color='#00CC96', decreasing_fillcolor='#00CC96'  # 下跌為綠
                ))
                
                # 加入 VWAP
                fig.add_trace(go.Scatter(x=hist_5m.index, y=hist_5m['VWAP'], mode='lines', name='VWAP (機構均價)', line=dict(color='purple', width=2)))
                
                # 加入壓力線與支撐線
                fig.add_hline(y=r1, line_dash="dash", line_color="#FF4B4B", annotation_text="今日壓力 (R1)", annotation_position="top right")
                fig.add_hline(y=s1, line_dash="dash", line_color="#00CC96", annotation_text="今日支撐 (S1)", annotation_position="bottom right")
                
                fig.update_layout(
                    height=450, margin=dict(l=0,r=0,t=0,b=0), 
                    xaxis_rangeslider_visible=False, template="plotly_dark", # 黑底專業感
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # --- 多空判定面板 ---
                last_vwap = hist_5m['VWAP'].iloc[-1]
                st.markdown("#### ⚡ 盤中動能判定")
                
                if curr_price > last_vwap:
                    st.markdown(f"<span class='badge-red'>大戶作多</span> 股價 (${curr_price:.2f}) 站上 VWAP (${last_vwap:.2f})，目標上看壓力線 ${r1:.2f}。", unsafe_allow_html=True)
                elif curr_price < last_vwap:
                    st.markdown(f"<span class='badge-green'>大戶倒貨</span> 股價 (${curr_price:.2f}) 跌破 VWAP (${last_vwap:.2f})，小心回測支撐線 ${s1:.2f}。", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span class='badge-gray'>多空交戰</span> 股價黏著 VWAP，等待方向表態。", unsafe_allow_html=True)
                    
        except Exception as e:
            st.error("無法取得資料，請確認今日是否開盤或股票代號是否正確。")
