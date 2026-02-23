import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 網頁基本設定
st.set_page_config(page_title="當沖狙擊雷達", page_icon="⚡", layout="centered")
st.title("⚡ 當沖高勝率狙擊雷達")

tw_tz = pytz.timezone('Asia/Taipei')
st.caption(f"⏱️ 系統更新時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M')}")

# --- 嚴格風控設定區 ---
st.markdown("### 🛡️ 交易風控設定")
col1, col2 = st.columns(2)
capital_limit = col1.number_input("當沖總資金上限 (元)", min_value=10000, value=500000, step=50000)
min_win_rate = col2.number_input("最低要求勝率 (%)", min_value=50, max_value=100, value=80, step=5)

st.markdown("---")

tab1, tab2 = st.tabs(["🎯 80%勝率狙擊名單", "📈 個股 5 分 K 線解析"])

# ==========================================
# 分頁 1：嚴格篩選雷達
# ==========================================
with tab1:
    st.markdown("### 🔎 盤面高勝率標的掃描")
    st.caption(f"篩選條件：過去一個月當沖獲利機率 ≥ {min_win_rate}%，且為爆量強勢股。")
    
    # 擴大觀察池以增加選股基數
    day_trade_pool = {
        "2603.TW": "長榮 (航運)", "3231.TW": "緯創 (AI)", "2382.TW": "廣達 (AI)", 
        "2317.TW": "鴻海 (權值)", "3034.TW": "聯詠 (IC)", "2609.TW": "陽明 (航運)",
        "2368.TW": "金像電 (PCB)", "3017.TW": "奇鋐 (散熱)", "3324.TW": "雙鴻 (散熱)",
        "2330.TW": "台積電 (權值)"
    }

    @st.cache_data(ttl=300)
    def scan_strict_candidates(pool, capital, required_win_rate):
        results = []
        for sym, desc in pool.items():
            try:
                stock = yf.Ticker(sym)
                # 抓取過去一個月資料進行「勝率回測」
                hist_1mo = stock.history(period="1mo")
                if len(hist_1mo) < 15: continue
                
                # 【勝率計算邏輯】：盤中最高價大於開盤價 1% (代表當沖有足夠肉可以吃)
                # True/False 陣列
                win_days = (hist_1mo['High'] - hist_1mo['Open']) / hist_1mo['Open'] >= 0.01 
                win_rate = (win_days.sum() / len(win_days)) * 100
                
                # 嚴格剔除低勝率
                if win_rate < required_win_rate:
                    continue
                
                today = hist_1mo.iloc[-1]
                yesterday = hist_1mo.iloc[-2]
                
                # 計算動能
                amplitude = ((today['High'] - today['Low']) / yesterday['Close']) * 100
                vol_ratio = today['Volume'] / yesterday['Volume'] if yesterday['Volume'] > 0 else 1
                curr_price = today['Close']
                
                # 【資金控管邏輯】：計算 50 萬可以買多少
                cost_per_lot = curr_price * 1000
                affordable_lots = int(capital // cost_per_lot)
                affordable_shares = int(capital // curr_price)
                
                trade_advice = f"可打 {affordable_lots} 張" if affordable_lots >= 1 else f"資金不足1張，限打零股 {affordable_shares} 股"
                
                # 只推薦有動能的股票
                if amplitude > 2.0 or vol_ratio > 1.2:
                    results.append({
                        "symbol": sym, "desc": desc, "price": curr_price,
                        "win_rate": win_rate, "amplitude": amplitude,
                        "trade_advice": trade_advice, "cost_per_lot": cost_per_lot
                    })
            except Exception:
                pass
        
        # 依勝率排序，高的排前面
        return sorted(results, key=lambda x: x['win_rate'], reverse=True)

    with st.spinner("嚴格過濾低勝率標命中，請稍候..."):
        targets = scan_strict_candidates(day_trade_pool, capital_limit, min_win_rate)
        
    if targets:
        st.success(f"🎉 篩選完成！今日共有 **{len(targets)}** 檔股票符合超過 {min_win_rate}% 勝率條件：")
        for t in targets:
            with st.container():
                st.markdown(f"#### 🎯 **{t['symbol']} {t['desc']}**")
                c1, c2, c3 = st.columns(3)
                c1.metric("即時股價", f"${t['price']:.1f}")
                c2.metric("歷史當沖勝率", f"{t['win_rate']:.1f}%")
                c3.metric("今日振幅", f"{t['amplitude']:.1f}%")
                
                st.info(f"💰 **資金分配建議**：{t['trade_advice']} (單張成本約 ${t['cost_per_lot']:,.0f})")
                st.markdown("---")
    else:
        st.error(f"⚠️ **目前盤面無任何股票符合「勝率大於 {min_win_rate}%」且具備動能的嚴格條件！**\n\n職業當沖客守則：沒有好獵物就不開槍，今日建議空手觀望，保護本金。")

# ==========================================
# 分頁 2：個股 5 分 K 線解析
# ==========================================
with tab2:
    st.markdown("### 🔍 進場點微觀視角 (5 分鐘 K 線)")
    ticker = st.text_input("輸入欲觀察的標的 (如 2603.TW)", value="2603.TW")
    
    if st.button("🔄 更新短線走勢"):
        st.cache_data.clear()
        
    if ticker:
        try:
            s = yf.Ticker(ticker)
            hist_5m = s.history(period="2d", interval="5m")
            
            if not hist_5m.empty:
                curr_price = hist_5m['Close'].iloc[-1]
                hist_5m['MA5'] = hist_5m['Close'].rolling(5).mean()
                hist_5m['MA12'] = hist_5m['Close'].rolling(12).mean()
                
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=hist_5m.index, open=hist_5m['Open'], high=hist_5m['High'], low=hist_5m['Low'], close=hist_5m['Close'], name='5分K'))
                fig.add_trace(go.Scatter(x=hist_5m.index, y=hist_5m['MA5'], mode='lines', name='MA5', line=dict(color='blue', width=1)))
                fig.add_trace(go.Scatter(x=hist_5m.index, y=hist_5m['MA12'], mode='lines', name='MA12', line=dict(color='orange', width=1)))
                
                fig.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
                
                last_ma5 = hist_5m['MA5'].iloc[-1]
                last_ma12 = hist_5m['MA12'].iloc[-1]
                if last_ma5 > last_ma12 and curr_price > last_ma5:
                    st.success("🟢 **5分K動能**：多頭排列，適合順勢作多。")
                elif last_ma5 < last_ma12 and curr_price < last_ma5:
                    st.error("🔴 **5分K動能**：空頭排列，慎防下殺。")
                else:
                    st.warning("🟡 **5分K動能**：均線糾結，動能不明確。")
        except Exception:
            st.error("無法取得資料。")
