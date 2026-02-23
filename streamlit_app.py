import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# --- 初始化 Session State (用於動態按鈕調整參數) ---
if 'win_rate' not in st.session_state:
    st.session_state.win_rate = 80
if 'rvol' not in st.session_state:
    st.session_state.rvol = 1.2

def relax_params():
    """一鍵放寬參數的 Callback 函數"""
    st.session_state.win_rate = 50
    st.session_state.rvol = 0.8

# --- 網頁與視覺主題設定 ---
st.set_page_config(page_title="Pro 當沖指揮中心", page_icon="⚡", layout="centered")

# 自訂 CSS (優化排版、加入模擬按鈕與更明確的色彩層級)
st.markdown("""
<style>
    .big-font { font-size:22px !important; font-weight: bold; color: #1E90FF; }
    .badge-red { background-color: #FF4B4B; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-green { background-color: #00CC96; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-gray { background-color: #555555; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .card { background-color: #f8f9fa; padding: 18px; border-radius: 12px; border-left: 6px solid #1E90FF; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);}
    .broker-btn { background-color: #FF8C00; color: white; padding: 6px 12px; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: bold; float: right; transition: 0.2s;}
    .broker-btn:hover { background-color: #E67E22; color: white; }
    .highlight-red { color: #FF4B4B; font-weight: bold; font-size: 16px; }
    .highlight-green { color: #00CC96; font-weight: bold; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Pro 當沖指揮中心")

# --- 台灣時間與市場狀態燈 ---
tw_tz = pytz.timezone('Asia/Taipei')
now = datetime.now(tw_tz)
current_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

market_open = now.replace(hour=9, minute=0, second=0)
market_close = now.replace(hour=13, minute=30, second=0)
is_open = market_open <= now <= market_close and now.weekday() < 5

if is_open:
    st.markdown(f"### 🟢 **盤中交易中** | {current_time_str}")
else:
    st.markdown(f"### 🔴 **市場已收盤/休市** | {current_time_str}")

# --- 參數設定區 ---
with st.expander("⚙️ 打擊區參數設定 (點擊展開/收合)", expanded=False):
    st.markdown("💡 *調整參數後，系統會即時重新掃描*")
    col1, col2 = st.columns(2)
    capital_limit = col1.number_input("總資金上限 (元)", value=500000, step=50000)
    # 綁定 session_state
    min_win_rate = col2.slider("要求勝率 (%)", min_value=50, max_value=100, step=5, key="win_rate")
    
    col3, col4 = st.columns(2)
    max_price = col3.number_input("單張股價上限 (元)", value=150.0, step=10.0)
    # 綁定 session_state
    min_rvol = col4.slider("爆量倍數 (RVOL)", min_value=0.5, max_value=5.0, step=0.1, key="rvol")
    
    # 隱藏手續費輸入框，底層直接寫死新光證券的 2.8 折
    fee_discount = 2.8

st.markdown("---")

# --- 雙分頁設計 ---
tab1, tab2 = st.tabs(["🎯 戰情雷達 (主力動向)", "📈 戰術圖表 (台股專屬 K 線)"])

# ==========================================
# 分頁 1：視覺化戰情雷達
# ==========================================
with tab1:
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
                
                # 回測期望值模擬 (勝率 * 平均獲利 - 敗率 * 平均虧損)
                ev = (win_rate/100 * est_gross_profit) - ((1 - win_rate/100) * (affordable_lots * 1000 * atr * 0.5))
                
                status_badge = "<span class='badge-red'>今日強勢 ⬆</span>" if today['Close'] > hist.iloc[-2]['Close'] else "<span class='badge-green'>今日弱勢 ⬇</span>"
                
                results.append({
                    "symbol": sym, "desc": desc, "price": curr_price,
                    "win_rate": win_rate, "rvol": rvol, "atr": atr,
                    "lots": affordable_lots, "net_profit": net_profit,
                    "sl": sl, "tp": tp, "status": status_badge, "ev": ev
                })
            except Exception:
                pass
        return sorted(results, key=lambda x: x['rvol'], reverse=True)

    with st.spinner("⚡ 啟動量化引擎，掃描市場資金流向..."):
        targets = scan_pro_candidates(strategic_pool, capital_limit, st.session_state.win_rate, fee_discount, st.session_state.rvol, max_price)
        
    if targets:
        st.success(f"🎯 鎖定 **{len(targets)}** 檔狙擊目標：")
        for t in targets:
            # 決定 EV 的顏色 (大於 0 顯示紅色，小於 0 顯示綠色)
            ev_color = '#FF4B4B' if t['ev'] > 0 else '#00CC96'
            
            # UI 優化：強化停損停利視覺、加入策略期望值與模擬下單按鈕
            st.markdown(f"""
            <div class="card">
                <div style="margin-bottom: 10px;">
                    <span class="big-font">{t['symbol']} {t['desc']}</span> &nbsp; {t['status']}
                    <a href="#" class="broker-btn">⚡ 帶入券商下單</a>
                </div>
                <div>
                    <b>最新股價：</b> ${t['price']:.2f} &nbsp;|&nbsp; 
                    <b>爆量倍數：</b> {t['rvol']:.1f}x &nbsp;|&nbsp; 
                    <b>歷史勝率：</b> {t['win_rate']:.0f}%
                </div>
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #ccc;">
                    🛒 <b>操作紀律：</b> 停利目標 <span class="highlight-red">${t['tp']:.2f}</span> / 停損防守 <span class="highlight-green">${t['sl']:.2f}</span><br>
                    💰 <b>資金配置：</b> 可打 {t['lots']} 張 (預估淨利 ${t['net_profit']:,.0f})<br>
                    📊 <b>策略期望值 (EV)：</b> <span style="color: {ev_color}; font-weight: bold;">${t['ev']:,.0f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("📉 目前無符合條件之標的。")
        # UX 優化：提供一鍵放寬標準的按鈕
        st.button("⚡ 一鍵套用寬鬆策略 (勝率50%, RVOL 0.8x)", on_click=relax_params, type="primary")

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
            hist_5m = s.history(period="1d", interval="5m") 
            hist_1d = s.history(period="5d", interval="1d")
            
            if not hist_5m.empty and len(hist_1d) >= 2:
                curr_price = hist_5m['Close'].iloc[-1]
                
                # --- 計算 Pivot Points (加入 R2, S2 涵蓋突破情境) ---
                yest = hist_1d.iloc[-2]
                pivot = (yest['High'] + yest['Low'] + yest['Close']) / 3
                r1 = (2 * pivot) - yest['Low']
                s1 = (2 * pivot) - yest['High']
                r2 = pivot + (yest['High'] - yest['Low'])
                s2 = pivot - (yest['High'] - yest['Low'])
                
                # --- 計算 VWAP ---
                hist_5m['Typical_Price'] = (hist_5m['High'] + hist_5m['Low'] + hist_5m['Close']) / 3
                hist_5m['VWAP'] = (hist_5m['Typical_Price'] * hist_5m['Volume']).cumsum() / hist_5m['Volume'].cumsum()
                
                # --- 繪製專業圖表 ---
                fig = go.Figure()
                
                fig.add_trace(go.Candlestick(
                    x=hist_5m.index, open=hist_5m['Open'], high=hist_5m['High'], low=hist_5m['Low'], close=hist_5m['Close'], 
                    name='5分K',
                    increasing_line_color='#FF4B4B', increasing_fillcolor='#FF4B4B', 
                    decreasing_line_color='#00CC96', decreasing_fillcolor='#00CC96'  
                ))
                
                fig.add_trace(go.Scatter(x=hist_5m.index, y=hist_5m['VWAP'], mode='lines', name='VWAP (機構均價)', line=dict(color='#9B59B6', width=2)))
                
                # 加入 R1, S1, R2, S2
                fig.add_hline(y=r2, line_dash="dot", line_color="#FF4B4B", opacity=0.4, annotation_text="強壓力 (R2)", annotation_position="top right")
                fig.add_hline(y=r1, line_dash="dash", line_color="#FF4B4B", annotation_text="今日壓力 (R1)", annotation_position="top right")
                fig.add_hline(y=s1, line_dash="dash", line_color="#00CC96", annotation_text="今日支撐 (S1)", annotation_position="bottom right")
                fig.add_hline(y=s2, line_dash="dot", line_color="#00CC96", opacity=0.4, annotation_text="強支撐 (S2)", annotation_position="bottom right")
                
                fig.update_layout(
                    height=500, margin=dict(l=0,r=0,t=0,b=0), 
                    xaxis_rangeslider_visible=False, template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    hovermode="x unified" # UX優化：讓游標懸浮時資訊更易讀
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # --- 多空判定面板 (修復價格突破邏輯) ---
                last_vwap = hist_5m['VWAP'].iloc[-1]
                st.markdown("#### ⚡ 盤中動能判定")
                
                if curr_price > last_vwap:
                    # 邏輯優化：判斷是否已突破 R1
                    if curr_price < r1:
                        target_msg = f"目標上看壓力線 **${r1:.2f}**"
                    else:
                        target_msg = f"已強勢突破 R1，下一目標上看 **${r2:.2f}**"
                    st.markdown(f"<span class='badge-red'>大戶作多</span> 股價 (${curr_price:.2f}) 站上 VWAP (${last_vwap:.2f})，{target_msg}。", unsafe_allow_html=True)
                
                elif curr_price < last_vwap:
                    # 邏輯優化：判斷是否已跌破 S1
                    if curr_price > s1:
                        target_msg = f"小心回測支撐線 **${s1:.2f}**"
                    else:
                        target_msg = f"已弱勢跌破 S1，下探強支撐 **${s2:.2f}**"
                    st.markdown(f"<span class='badge-green'>大戶倒貨</span> 股價 (${curr_price:.2f}) 跌破 VWAP (${last_vwap:.2f})，{target_msg}。", unsafe_allow_html=True)
                
                else:
                    st.markdown(f"<span class='badge-gray'>多空交戰</span> 股價黏著 VWAP，等待方向表態。", unsafe_allow_html=True)
                    
        except Exception as e:
            st.error("無法取得資料，請確認今日是否開盤或股票代號是否正確。")
