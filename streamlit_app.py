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

st.set_page_config(page_title="波段紀律系統 Pro Max", page_icon="💎", layout="wide")

st.markdown("""
<style>
    .big-font { font-size:22px !important; font-weight: bold; color: #1E90FF; }
    .report-card { background-color: #1E1E1E; color: white; padding: 20px; border-radius: 12px; border-top: 5px solid #1E90FF; margin-top: 15px; }
    .metric-box { background-color: #2b2b2b; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #444; min-width: 120px; flex: 1; margin-bottom: 10px;}
    .news-box { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 5px solid #FFD700; margin-top: 10px; font-size: 14px;}
    .tactic-box { background-color: rgba(255, 140, 0, 0.1); border-left: 5px solid #FF8C00; padding: 15px; border-radius: 8px; margin-top: 10px; }
    .highlight-red { color: #FF4B4B; font-weight: bold; }
    .highlight-green { color: #00CC96; font-weight: bold; }
    .highlight-blue { color: #1E90FF; font-weight: bold; }
    .card { background-color: #f8f9fa; color: #333; padding: 18px; border-radius: 12px; border-left: 6px solid #FF8C00; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);}
    .badge-red { background-color: #FF4B4B; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-green { background-color: #00CC96; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-gold { background-color: #FFD700; color: #333; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .badge-us { background-color: #1E90FF; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

colA, colB = st.columns([3, 1])
with colA:
    st.title("💎 波段紀律交易系統 (Pro Max)")
with colB:
    st.write("") 
    if st.button("🔄 全局刷新與資料同步", type="primary", use_container_width=True):
        st.cache_data.clear()

tw_tz = pytz.timezone('Asia/Taipei')
st.caption(f"系統時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M')} | 修復：手機版 HTML 渲染器衝突與圖表繪製")

# =====================================================
# 雙引擎股池設定
# =====================================================
tw_pool = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2382.TW": "廣達", "3231.TW": "緯創",
    "2376.TW": "技嘉", "1519.TW": "華城", "1513.TW": "中興電", "1504.TW": "東元", "1514.TW": "亞力",
    "2603.TW": "長榮", "2609.TW": "陽明", "2618.TW": "長榮航", "2365.TW": "昆盈", "3324.TW": "雙鴻",
    "3017.TW": "奇鋐", "3034.TW": "聯詠", "3443.TW": "創意", "3661.TW": "世芯-KY", "3450.TW": "聯鈞",
    "0050.TW": "台灣50", "0056.TW": "高股息", "2881.TW": "富邦金", "2891.TW": "中信金"
}
us_pool = {
    "NVDA": "輝達", "TSLA": "特斯拉", "AAPL": "蘋果", "MSFT": "微軟", "GOOGL": "谷歌",
    "META": "Meta", "AMZN": "亞馬遜", "AMD": "超微", "PLTR": "帕蘭泰爾", "ARM": "安謀",
    "AVGO": "博通", "SMCI": "美超微", "CRWD": "CrowdStrike", "COIN": "微策略",
    "TSM": "台積電 ADR", "QQQ": "納斯達克 ETF", "SPY": "標普500 ETF"
}
combined_pool = {**tw_pool, **us_pool}

# =====================================================
# 共用核心函數
# =====================================================
@st.cache_data(ttl=600)
def get_realtime_fx():
    try:
        fx = yf.download("TWD=X", period="1d", progress=False)
        if isinstance(fx.columns, pd.MultiIndex): fx.columns = fx.columns.droplevel(1)
        return float(fx['Close'].iloc[-1])
    except:
        return 32.5 

def is_us_stock(ticker):
    return not (".TW" in ticker.upper() or ".TWO" in ticker.upper())

def smart_ticker_lookup(user_input):
    user_input = str(user_input).strip().upper()
    if not user_input: return None
    if ".TW" in user_input or ".TWO" in user_input: return user_input
    for sym, name in combined_pool.items():
        if user_input in name.upper() or user_input in sym.upper(): return sym
    if re.match(r'^[A-Z]+$', user_input): return user_input
    if user_input.isdigit(): return user_input + ".TW"
    return user_input

@st.cache_data(ttl=600)
def market_filter():
    try:
        twii = yf.download("^TWII", period="3mo", progress=False)
        spy = yf.download("SPY", period="3mo", progress=False)
        if isinstance(twii.columns, pd.MultiIndex): twii.columns = twii.columns.droplevel(1)
        if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.droplevel(1)
        twii['20MA'] = twii['Close'].rolling(20).mean()
        spy['20MA'] = spy['Close'].rolling(20).mean()
        tw_status = "🟢 多頭" if twii.iloc[-1]['Close'] > twii.iloc[-1]['20MA'] else "🔴 空頭"
        us_status = "🟢 多頭" if spy.iloc[-1]['Close'] > spy.iloc[-1]['20MA'] else "🔴 空頭"
        return f"🇹🇼 台股: {tw_status} ｜ 🇺🇸 美股: {us_status}"
    except:
        return "⚪ 大盤數據讀取異常"

def calculate_indicators(hist):
    hist = hist.copy()
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
    hist['Recent_High20'] = hist['High'].rolling(20).max().shift(1)
    return hist

st.info(f"📊 全球大盤月線格局 ➔ {market_filter()}")

tab1, tab2, tab3, tab4 = st.tabs(["🎯 AI 雷達掃描", "🏥 個股深度診斷", "📊 實戰資產日誌", "🧪 專業回測引擎"])

# =====================================================
# TAB 1: AI 雷達掃描
# =====================================================
with tab1:
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    market_choice = col_s1.radio("選擇雷達掃描市場", ["🇹🇼 台股強勢池", "🇺🇸 美股巨頭池", "🌍 全球火力全開"], horizontal=True)
    capital_input = col_s2.number_input("設定台幣總資金 (NT$)", value=50000, step=10000)
    current_fx = get_realtime_fx()
    fx_rate = col_s3.number_input("即時美金匯率", value=float(current_fx), step=0.01)
    
    @st.cache_data(ttl=600)
    def auto_screener(pool_choice, capital_ntd, fx):
        if pool_choice == "🇹🇼 台股強勢池": target_pool = tw_pool
        elif pool_choice == "🇺🇸 美股巨頭池": target_pool = us_pool
        else: target_pool = combined_pool
            
        results = []
        for sym, name in target_pool.items():
            try:
                hist = yf.download(sym, period="6mo", progress=False)
                if hist.empty: continue
                if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.droplevel(1)
                if len(hist) < 30: continue
                
                hist = calculate_indicators(hist)
                today = hist.iloc[-1]
                
                if today['Close'] < today['20MA']: continue 
                if today['RSI'] > 80 or today['RSI'] < 40: continue 
                
                score = 0
                if today['5MA'] > today['10MA'] > today['20MA']: score += 30
                if today['MACD'] > today['Signal']: score += 20
                if today['Close'] > today['Recent_High20']: score += 20
                avg_vol_5d = hist['Volume'].rolling(5).mean().shift(1).iloc[-1]
                if avg_vol_5d > 0 and today['Volume'] > avg_vol_5d * 1.2: score += 10
                
                if score >= 40: 
                    _is_us = is_us_stock(sym)
                    currency_sym = "US$" if _is_us else "NT$"
                    exchange_rate = fx if _is_us else 1.0
                    
                    entry = today['Close']
                    stop = today['20MA'] * 0.99
                    atr = today['ATR']
                    buy_price = entry - (atr * 0.15) 
                    tp = entry + (atr * 3) 
                    
                    risk_per_trade_ntd = capital_ntd * 0.02
                    risk_per_share_local = (buy_price - stop) * exchange_rate
                    if risk_per_share_local <= 0: continue
                    shares = int(risk_per_trade_ntd // risk_per_share_local)
                    if shares < 1: continue

                    if _is_us and (shares * buy_price) < 100: continue

                    win_days = (hist['High'] - hist['Open']) / hist['Open'] >= 0.01 
                    win_rate = (win_days.sum() / len(win_days)) * 100
                    
                    trade_value_local = shares * buy_price * exchange_rate
                    est_gross_profit_local = shares * (tp - buy_price) * exchange_rate
                    
                    if _is_us:
                        fee_usd = (shares * buy_price) * 0.001
                        friction_local = (fee_usd * 2) * exchange_rate 
                    else:
                        fee = max(1, int(trade_value_local * 0.001425 * 0.28))
                        tax = int(trade_value_local * 0.003)
                        friction_local = (fee * 2) + tax
                        
                    net_profit_local = est_gross_profit_local - friction_local
                    if net_profit_local <= 0: continue
                    ev_local = (win_rate/100 * est_gross_profit_local) - ((1 - win_rate/100) * (shares * (buy_price - stop) * exchange_rate))
                    
                    prev_close = hist['Close'].shift(1).iloc[-1]
                    status_badge = "<span class='badge-red'>今日強勢 ⬆</span>" if today['Close'] > prev_close else "<span class='badge-green'>今日拉回 ⬇</span>"
                    market_badge = "<span class='badge-us'>🇺🇸 美股</span>" if _is_us else "<span class='badge-gold'>🇹🇼 台股</span>"
                    
                    results.append({
                        "代號": sym, "clean_sym": sym.replace('.TW', '').replace('.TWO', ''), "名稱": name, 
                        "現價": entry, "buy_price": buy_price, "停損": stop, "tp": tp, "建議股數": shares, 
                        "評分": score, "win_rate": win_rate, "net_profit": net_profit_local, 
                        "friction": friction_local, "ev": ev_local, "status": status_badge,
                        "currency": currency_sym, "market": market_badge
                    })
            except: pass
        return sorted(results, key=lambda x: x['評分'], reverse=True)

    if st.button("🚀 啟動 AI 掃描引擎", type="primary", use_container_width=True):
        with st.spinner("掃描全球數據，精算風控與目標價..."):
            targets = auto_screener(market_choice, capital_input, fx_rate)
            if targets:
                st.success(f"🎯 嚴選 {len(targets)} 檔合規標的：")
                for i, t in enumerate(targets):
                    ev_color = '#FF4B4B' if t['ev'] > 0 else '#00CC96'
                    st.markdown(f"""
                    <div class="card">
                        <div style="margin-bottom: 10px;">
                            {t['market']} <span class="big-font">{t['clean_sym']} {t['名稱']}</span> &nbsp; {t['status']}
                        </div>
                        <div>
                            <b>最新股價：</b> {t['currency']}{t['現價']:.2f} &nbsp;|&nbsp; 
                            <b>歷史勝率：</b> {t['win_rate']:.0f}%
                        </div>
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #ccc;">
                            🛒 <b>紀律：</b> 買入 <span class="highlight-blue">{t['currency']}{t['buy_price']:.2f}</span> | 停利 <span class="highlight-red">{t['currency']}{t['tp']:.2f}</span> | 月線停損 <span class="highlight-green">{t['currency']}{t['停損']:.2f}</span><br>
                            💰 <b>配置：</b> 可打 <b>{t['建議股數']} 股</b> (估淨利 NT$ {t['net_profit']:,.0f})<br>
                            📊 <b>戰力：</b> <span style="color: #1E90FF; font-weight: bold;">{t['評分']:.1f} 分</span> (EV: <span style="color: {ev_color}; font-weight: bold;">NT$ {t['ev']:,.0f}</span>)
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.code(t['clean_sym'], language="text")
            else:
                st.warning("📉 目前無符合高勝率且合規之標的，建議空手。")

# =====================================================
# TAB 2: 個股深度診斷與建倉 (修復 HTML 渲染)
# =====================================================
with tab2:
    st.markdown("### 🤖 跨國個股深度診斷")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    quick_select_list = ["--- 自行輸入 ---"] + [f"{k.replace('.TW','')} {v}" for k, v in combined_pool.items()]
    quick_choice = col1.selectbox("📋 從優質股池快速選擇", quick_select_list)
    
    if quick_choice != "--- 自行輸入 ---":
        default_input = quick_choice.split(" ")[0]
    else:
        default_input = "NVDA"
        
    user_input = col2.text_input("✍️ 或自行輸入代號/中文", value=default_input)
    btn = col3.button("🧠 執行深度診斷", type="primary", use_container_width=True)

    if btn:
        st.cache_data.clear()
        parsed = smart_ticker_lookup(user_input)
        _is_us = is_us_stock(parsed)
        cur_sym = "US$" if _is_us else "NT$"
        
        with st.spinner(f"正在全方位解析 {parsed} ..."):
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
                
                exchange_rate = fx_rate if _is_us else 1.0
                risk_per_trade_ntd = capital_input * 0.02
                risk_per_share_local = (entry - stop) * exchange_rate
                shares = int(risk_per_trade_ntd // risk_per_share_local) if risk_per_share_local > 0 else 0

                if not week_trend_ok: advice, color = "🔴 嚴格禁止作多 (週線為空頭格局)", "#FF4B4B"
                elif score > 60: advice, color = "🟢 建議佈局做多 (動能強勁)", "#00CC96"
                elif score > 40: advice, color = "🟡 建議等待拉回 (靠近均線再行評估)", "#FFD700"
                else: advice, color = "🔴 不建議進場 (動能疲弱)", "#FF4B4B"

                flags = []
                if today['RSI'] > 80: flags.append("短線 RSI 過熱")
                if today['Close'] < today['20MA']: flags.append("股價跌破生命月線")
                if not week_trend_ok: flags.append("長線 (週 20MA) 趨勢向下")
                if _is_us and (shares * entry) < 100:
                    flags.append(f"單筆總額不足 100 美元，不符國泰低消門檻。")

                dist_to_5ma = (today['Close'] - today['5MA']) / today['5MA']
                dist_to_20ma = (today['Close'] - today['20MA']) / today['20MA']
                
                # 將原先的 Markdown 改為 HTML 標籤，徹底解決手機排版衝突
                if score < 40 or today['Close'] < today['20MA']:
                    tactic = "⛔ <b>空手觀望</b>：目前趨勢偏空或動能不足，強烈建議保留資金，不要建倉。"
                elif today['RSI'] > 75 or dist_to_5ma > 0.05:
                    tactic = f"⚠️ <b>高檔分批建倉 (乖離過大)</b>：股價偏離 5MA 太遠。建議先用 <b>30% 資金（約 {max(1, int(shares*0.3))} 股）</b> 試單，剩餘掛在 10MA（{cur_sym}{today['10MA']:.1f}）等拉回低接。"
                elif today['MACD'] > today['Signal'] and today['RSI'] <= 65 and dist_to_20ma < 0.08:
                    tactic = f"🔥 <b>一次建倉 (黃金起漲點)</b>：動能強且距防守線近，風控極佳。建議於 <b>{cur_sym}{entry:.1f}</b> 附近，一次買齊目標 <b>{shares} 股</b>。"
                elif today['Close'] <= today['10MA'] and today['Close'] > today['20MA']:
                    tactic = f"🛡️ <b>左側分批接刀</b>：回測月線中。建議現價買 <b>50%（約 {max(1, int(shares*0.5))} 股）</b>，跌至 20MA（{cur_sym}{today['20MA']:.1f}）再加碼。跌破 20MA 全停損。"
                else:
                    tactic = f"⚖️ <b>震盪試單</b>：走勢震盪，建議先打 <b>50% 資金（約 {max(1, int(shares*0.5))} 股）</b> 試水溫，突破前高再加碼。"

                stock_name = combined_pool.get(parsed, parsed.replace('.TW','').replace('.TWO',''))
                market_tag = "🇺🇸" if _is_us else "🇹🇼"
                
                # 解決亂碼問題：完全移除 HTML 字串內的空行，並加入 flex-wrap
                st.markdown(f"""
                <div class="report-card">
                    <h3 style="margin-top:0;">{market_tag} {stock_name} 戰略診斷報告</h3>
                    <div style="background-color: {color}22; border-left: 5px solid {color}; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                        <span style="font-size: 18px; color: {color}; font-weight: bold;">{advice} (AI 評分: {score:.1f}/100)</span>
                    </div>
                    <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                        <div class="metric-box"><b>現價/進場區</b><br><span style="color:#1E90FF; font-size:18px;">{cur_sym}{entry:.1f}</span></div>
                        <div class="metric-box"><b>防守停損價</b><br><span style="color:#00CC96; font-size:18px;">{cur_sym}{stop:.1f}</span></div>
                        <div class="metric-box"><b>波段目標價</b><br><span style="color:#FF4B4B; font-size:18px;">{cur_sym}{target:.1f}</span></div>
                        <div class="metric-box"><b>2%風控可買</b><br><span style="color:#FFD700; font-size: 18px; font-weight: bold;">{shares} 股</span></div>
                    </div>
                    <div class="tactic-box">
                        <h4 style="margin-top:0; color:#FF8C00;">🛒 AI 資金建倉兵法</h4>
                        <span style="font-size:16px;">{tactic}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if flags:
                    for f in flags: st.error(f"⚠ {f}")
                else:
                    st.success("✅ 目前技術面與風控皆完美符合做多紀律！")

                st.markdown("#### 📊 專業技術圖表檢視")
                
                # 
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
                fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='日K'), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=hist['10MA'], name='10MA', line=dict(color='#FFD700', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=hist['20MA'], name='20MA (月線)', line=dict(color='#9B59B6', width=2)), row=1, col=1)
                
                macd_colors = ['#FF4B4B' if val > 0 else '#00CC96' for val in (hist['MACD'] - hist['Signal'])]
                
                # --- 修復重點：完成中斷的 MACD 繪圖邏輯 ---
                fig.add_trace(go.Bar(x=hist.index, y=(hist['MACD'] - hist['Signal']), marker_color=macd_colors, name='MACD 柱狀圖'), row=2, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=hist['MACD'], name='MACD', line=dict(color='#1E90FF', width=1)), row=2, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=hist['Signal'], name='Signal', line=dict(color='#FF8C00', width=1)), row=2, col=1)

                fig.update_layout(height=650, margin=dict(l=0, r=0, t=30, b=0), showlegend=False, 
                                  xaxis_rangeslider_visible=False, template="plotly_dark")
                
                # 渲染圖表
                st.plotly_chart(fig, use_container_width=True)

                # 顯示相關新聞 (如果有撈取到的話)
                if news_data:
                    st.markdown("#### 📰 相關市場新聞")
                    for news in news_data[:3]:
                        title = news.get('title', '無標題新聞')
                        link = news.get('link', '#')
                        st.markdown(f"<div class='news-box'>🔗 <a href='{link}' target='_blank' style='color: #1E90FF; text-decoration: none;'>{title}</a></div>", unsafe_allow_html=True)
                        
            else:
                st.error("📉 找不到該標的之歷史資料，請確認代碼是否輸入正確。")

# =====================================================
# TAB 3: 實戰資產日誌 (補齊結構)
# =====================================================
with tab3:
    st.markdown("### 📊 實戰資產日誌")
    st.info("💡 此區塊目前為展示用數據。未來可串接資料庫（如 SQLite 或 Google Sheets）來記錄你真實的交易點位與損益。")
    
    mock_data = pd.DataFrame({
        "交易日": ["2026-02-20", "2026-02-23"],
        "市場": ["🇹🇼 台股", "🇺🇸 美股"],
        "代號": ["2330.TW", "NVDA"],
        "買入均價": [850, 120],
        "持有股數": [1000, 50],
        "當前市價": [875, 128],
        "未實現損益": ["+25,000", "+400"]
    })
    st.dataframe(mock_data, use_container_width=True, hide_index=True)

# =====================================================
# TAB 4: 專業回測引擎 (補齊結構)
# =====================================================
with tab4:
    st.markdown("### 🧪 專業回測引擎")
    st.warning("🚧 此模組尚在開發中。未來將支援自定義策略（例如：5MA 上穿 20MA、RSI 黃金交叉）的歷史勝率回測功能。")

