import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 網頁基本設定
st.set_page_config(page_title="職業當沖系統", page_icon="⚡", layout="centered")
st.title("⚡ 職業級：戰略當沖決策系統")
st.caption("融合 VWAP加權均價、ATR波動率與 RVOL爆量指標")

tw_tz = pytz.timezone('Asia/Taipei')
st.caption(f"⏱️ 系統更新時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M')}")

# --- 嚴格風控與成本設定區 ---
st.markdown("### 🛡️ 資金控管與紀律設定")
col1, col2 = st.columns(2)
capital_limit = col1.number_input("總資金上限 (元)", value=500000, step=50000)
min_win_rate = col2.number_input("歷史勝率要求 (%)", min_value=50, max_value=100, value=80, step=5)

col3, col4 = st.columns(2)
fee_discount = col3.number_input("券商手續費折數", value=2.8, step=0.1)
min_rvol = col4.number_input("最低爆量倍數 (RVOL)", value=1.2, step=0.1)

st.markdown("---")

tab1, tab2 = st.tabs(["🎯 AI 戰略選股雷達", "📈 職業 5 分 K 線 (內建 VWAP)"])

# ==========================================
# 分頁 1：戰略主題篩選雷達 (加入 ATR 與 RVOL)
# ==========================================
with tab1:
    st.markdown("### 🔎 主題強勢股掃描")
    
    strategic_pool = {
        "2634.TW": "漢翔", "2314.TW": "台揚", "8033.TWO": "雷虎", 
        "2009.TW": "第一銅", "1605.TW": "華新", "8390.TWO": "金益鼎",
        "2365.TW": "昆盈", "4562.TWO": "穎漢", "6188.TWO": "廣明", 
        "2371.TW": "大同", "1608.TW": "華榮", "1609.TW": "大亞", "1618.TW": "合機"
    }

    @st.cache_data(ttl=300)
    def scan_pro_candidates(pool, capital, required_win_rate, discount, rvol_req):
        results = []
        for sym, desc in pool.items():
            try:
                stock = yf.Ticker(sym)
                hist = stock.history(period="1mo")
                if len(hist) < 15: continue
                
                # 計算勝率
                win_days = (hist['High'] - hist['Open']) / hist['Open'] >= 0.01 
                win_rate = (win_days.sum() / len(win_days)) * 100
                if win_rate < required_win_rate: continue
                
                today = hist.iloc[-1]
                curr_price = today['Close']
                
                # 限制單張低於 5 萬與資金上限
                cost_per_lot = curr_price * 1000
                if cost_per_lot > 50000: continue
                affordable_lots = int(capital // cost_per_lot)
                if affordable_lots < 1: continue
                
                # 計算 RVOL (相對成交量)
                avg_vol_10d = hist['Volume'].rolling(10).mean().iloc[-2]
                rvol = today['Volume'] / avg_vol_10d if avg_vol_10d > 0 else 1
                if rvol < rvol_req: continue # 剔除沒有爆量的死水股
                
                # 計算 ATR (真實波動幅度，取近 14 天)
                hist['TR'] = hist['High'] - hist['Low']
                atr = hist['TR'].rolling(14).mean().iloc[-1]
                
                # 制定交易計畫 (盈虧比 1:2)
                stop_loss = curr_price - (atr * 0.5) # 跌破半個波動幅停損
                take_profit = curr_price + (atr * 1.0) # 賺取一個波動幅停利
                
                # 計算淨利
                est_gross_profit = affordable_lots * 1000 * (atr * 1.0)
                fee_rate = 0.001425 * (discount / 10)
                friction = affordable_lots * ((curr_price * 1000 * fee_rate * 2) + (curr_price * 1000 * 0.0015))
                net_profit = est_gross_profit - friction
                if net_profit <= 0: continue
                
                results.append({
                    "symbol": sym, "desc": desc, "price": curr_price,
                    "win_rate": win_rate, "rvol": rvol, "atr": atr,
                    "lots": affordable_lots, "net_profit": net_profit,
                    "sl": stop_loss, "tp": take_profit
                })
            except Exception:
                pass
        return sorted(results, key=lambda x: x['rvol'], reverse=True) # 依爆量程度排序

    with st.spinner("AI 正在計算 RVOL 與 ATR 波動率..."):
        targets = scan_pro_candidates(strategic_pool, capital_limit, min_win_rate, fee_discount, min_rvol)
        
    if targets:
        st.success(f"🔥 盤面激戰中！共 **{len(targets)}** 檔標的爆量且符合高勝率：")
        for t in targets:
            with st.container():
                st.markdown(f"#### 🎯 **{t['symbol']} {t['desc']}**")
                c1, c2, c3 = st.columns(3)
                c1.metric("即時股價", f"${t['price']:.2f}")
                c2.metric("爆量倍數 (RVOL)", f"{t['rvol']:.1f}x")
                c3.metric("勝率", f"{t['win_rate']:.0f}%")
                
                st.info(f"📋 **操盤計畫 (盈虧比 1:2)**：\n"
                        f"🟢 建議停利：**${t['tp']:.2f}** (預估實賺 ${t['net_profit']:,.0f})\n"
                        f"🔴 嚴格停損：**${t['sl']:.2f}**\n"
                        f"💼 資金分配：滿載可打 **{t['lots']} 張**")
                st.markdown("---")
    else:
        st.warning(f"👀 目前無標的達標。可能原因：盤面量能萎縮 (RVOL < {min_rvol}) 或價差被手續費吃光。等待才是最好的交易！")

# ==========================================
# 分頁 2：職業 5 分 K 線解析 (導入 VWAP)
# ==========================================
with tab2:
    st.markdown("### 🔍 當沖神針：VWAP 均價線解析")
    ticker = st.text_input("輸入欲觀察的戰略股 (如 2371.TW)", value="2371.TW")
    
    if st.button("🔄 更新 5 分 K 線與 VWAP"):
        st.cache_data.clear()
        
    if ticker:
        try:
            s = yf.Ticker(ticker)
            hist_5m = s.history(period="1d", interval="5m") # 只抓今日，計算當日 VWAP
            
            if not hist_5m.empty:
                curr_price = hist_5m['Close'].iloc[-1]
                
                # 計算當日 VWAP (成交量加權平均價)
                hist_5m['Typical_Price'] = (hist_5m['High'] + hist_5m['Low'] + hist_5m['Close']) / 3
                hist_5m['VWAP'] = (hist_5m['Typical_Price'] * hist_5m['Volume']).cumsum() / hist_5m['Volume'].cumsum()
                
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=hist_5m.index, open=hist_5m['Open'], high=hist_5m['High'], low=hist_5m['Low'], close=hist_5m['Close'], name='5分K'))
                fig.add_trace(go.Scatter(x=hist_5m.index, y=hist_5m['VWAP'], mode='lines', name='VWAP (機構均價)', line=dict(color='purple', width=2, dash='dot')))
                
                fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
                
                last_vwap = hist_5m['VWAP'].iloc[-1]
                if curr_price > last_vwap:
                    st.success(f"🟢 **大戶多頭**：目前股價 (${curr_price:.2f}) 站上 VWAP (${last_vwap:.2f})，市場平均成本為多方掌控，偏多操作。")
                elif curr_price < last_vwap:
                    st.error(f"🔴 **大戶空頭**：目前股價 (${curr_price:.2f}) 跌破 VWAP (${last_vwap:.2f})，套牢賣壓重，反彈偏空操作。")
                else:
                    st.warning("🟡 **多空交戰**：股價黏著 VWAP，方向未明。")
        except Exception:
            st.error("無法取得資料，請確認今日是否開盤或代號正確。")
