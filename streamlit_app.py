import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pytz
import os

st.set_page_config(page_title="波段狙擊事業管理", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .big-font { font-size:22px !important; font-weight: bold; color: #1E90FF; }
    .card { background-color: #f8f9fa; padding: 18px; border-radius: 12px; border-left: 6px solid #00CC96; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);}
    .metric-box { background-color: #1E1E1E; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #333;}
    .highlight-red { color: #FF4B4B; font-weight: bold; font-size: 16px; }
    .highlight-green { color: #00CC96; font-weight: bold; font-size: 16px; }
    .highlight-blue { color: #1E90FF; font-weight: bold; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

st.title("🚀 短線波段狙擊系統 (Swing Trade)")
tw_tz = pytz.timezone('Asia/Taipei')
now = datetime.now(tw_tz)
st.caption(f"系統時間：{now.strftime('%Y-%m-%d %H:%M')} | 策略核心：日 K 線均線糾結突破、MACD 波段發動")

tab1, tab2, tab3 = st.tabs(["🎯 波段起漲雷達 (AI選股)", "📈 日 K 戰術圖表 (指標檢視)", "📊 翻倍進度與日誌"])

# 擴充波段優質股池 (加入中大型成長股與強勢題材)
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

# ==========================================
# 分頁 1：波段起漲雷達
# ==========================================
with tab1:
    st.markdown("### 🔍 尋找「剛剛發動」的短線波段股")
    st.caption("過濾條件：股價站上 10MA (短線生命線)、MACD 翻紅或黃金交叉、成交量放大。")
    
    col1, col2 = st.columns(2)
    capital = col1.number_input("預計投入單檔資金 (元)", value=3000, step=1000)
    vol_multiplier = col2.slider("日均量放大倍數要求", 1.0, 3.0, value=1.2, step=0.1)
    
    @st.cache_data(ttl=3600) # 盤後看，快取一小時即可
    def scan_swing_candidates(pool, cap, vol_req):
        results = []
        for sym, desc in pool.items():
            try:
                stock = yf.Ticker(sym)
                hist = stock.history(period="3mo") # 抓3個月來算均線
                if len(hist) < 30: continue
                
                # 計算波段均線
                hist['5MA'] = hist['Close'].rolling(5).mean()
                hist['10MA'] = hist['Close'].rolling(10).mean()
                hist['20MA'] = hist['Close'].rolling(20).mean() # 月線
                
                # 計算 MACD
                exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
                exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
                hist['MACD'] = exp1 - exp2
                hist['Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
                hist['Hist'] = hist['MACD'] - hist['Signal']
                
                today = hist.iloc[-1]
                yesterday = hist.iloc[-2]
                curr_price = today['Close']
                
                # 【波段核心濾網】
                # 1. 股價必須在 10MA 之上 (代表短線趨勢偏多)
                if curr_price < today['10MA']: continue
                
                # 2. 均線量能：今日量大於 5 日均量
                avg_vol_5d = hist['Volume'].rolling(5).mean().iloc[-2]
                vol_ratio = today['Volume'] / avg_vol_5d if avg_vol_5d > 0 else 1
                if vol_ratio < vol_req: continue
                
                # 3. MACD 趨勢向上 (柱狀圖翻紅或持續擴大)
                if today['Hist'] < 0 and today['Hist'] <= yesterday['Hist']: continue
                
                # 買進策略計算
                shares = int(cap // curr_price)
                if shares < 1: continue
                
                # ATR 計算停損停利 (波段抓比較大)
                hist['TR'] = hist['High'] - hist['Low']
                atr = hist['TR'].rolling(14).mean().iloc[-1]
                
                # 波段建議：靠近 5MA 買進最安全，跌破 10MA 停損
                buy_zone = f"${today['5MA']:.1f} ~ ${curr_price:.1f}"
                sl = today['10MA'] * 0.99 # 跌破 10MA 再多抓 1% 緩衝
                tp = curr_price + (atr * 3) # 波段抓 3 個 ATR 的大獲利
                
                # 評分：多頭排列 (5>10>20) 分數最高
                trend_score = 0
                if today['5MA'] > today['10MA'] > today['20MA']: trend_score += 50
                trend_score += min(vol_ratio * 10, 30)
                if today['MACD'] > today['Signal']: trend_score += 20
                
                status = "🔥 多頭爆發" if today['5MA'] > today['10MA'] > today['20MA'] else "📈 底部起漲"
                clean_sym = sym.replace('.TW', '').replace('.TWO', '')
                
                results.append({
                    "symbol": sym, "clean_sym": clean_sym, "desc": desc, "price": curr_price,
                    "buy_zone": buy_zone, "sl": sl, "tp": tp, "shares": shares,
                    "vol_ratio": vol_ratio, "trend_score": trend_score, "status": status,
                    "ma5": today['5MA'], "ma10": today['10MA'], "ma20": today['20MA']
                })
            except: pass
        return sorted(results, key=lambda x: x['trend_score'], reverse=True)

    if st.button("🚀 啟動波段 AI 雷達", type="primary", use_container_width=True):
        with st.spinner("掃描日K線級別趨勢，尋找波段黑馬..."):
            targets = scan_swing_candidates(strategic_pool, capital, vol_multiplier)
            
        if targets:
            st.success(f"🎯 成功鎖定 **{len(targets)}** 檔波段發動標的：")
            for t in targets:
                with st.container():
                    st.markdown(f"""
                    <div class="card">
                        <div style="margin-bottom: 10px;">
                            <span class="big-font">{t['clean_sym']} {t['desc']}</span> &nbsp; <span class='badge-red'>{t['status']}</span>
                            <div style="float: right; color: #888;">AI 趨勢評分: {t['trend_score']:.0f}</div>
                        </div>
                        <div>
                            <b>最新日收盤：</b> ${t['price']:.2f} &nbsp;|&nbsp; 
                            <b>量能放大：</b> {t['vol_ratio']:.1f}x &nbsp;|&nbsp; 
                            <b>月線(20MA)：</b> ${t['ma20']:.1f}
                        </div>
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #ccc;">
                            💼 <b>波段紀律：</b> 佈局區間 <span class="highlight-blue">{t['buy_zone']}</span> | 目標停利 <span class="highlight-red">${t['tp']:.1f}</span> | 防守 10MA <span class="highlight-green">${t['sl']:.1f}</span><br>
                            💰 <b>零股配置：</b> 此資金量可佈局 <b>{t['shares']} 股</b>，適合持有 3~10 個交易日。
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.code(t['clean_sym'], language="text")
        else:
            st.warning("📉 目前無符合波段起漲條件之標的，大盤可能處於回檔或震盪期，建議持幣觀望。")

# ==========================================
# 分頁 2：日 K 戰術圖表
# ==========================================
with tab2:
    st.markdown("### 📊 日 K 線波段解析")
    user_search = st.text_input("輸入欲分析的股票 (如: 2330 或 台積電)", placeholder="支援中文搜尋...", value="2330")
    
    if user_search:
        parsed_ticker = smart_ticker_lookup(user_search)
        if parsed_ticker:
            try:
                s = yf.Ticker(parsed_ticker)
                hist = s.history(period="6mo", interval="1d") # 波段看 6 個月
                
                if not hist.empty:
                    # 計算均線
                    hist['5MA'] = hist['Close'].rolling(5).mean()
                    hist['10MA'] = hist['Close'].rolling(10).mean()
                    hist['20MA'] = hist['Close'].rolling(20).mean()
                    
                    # 計算 MACD
                    exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
                    exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
                    hist['MACD'] = exp1 - exp2
                    hist['Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
                    hist['Hist'] = hist['MACD'] - hist['Signal']
                    
                    st.markdown(f"#### 📌 {user_search} ({parsed_ticker.replace('.TW','')}) 日 K 線趨勢")
                    
                    # 繪製主圖 (K線 + 均線)
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], 
                        name='日K', increasing_line_color='#FF4B4B', increasing_fillcolor='#FF4B4B', decreasing_line_color='#00CC96', decreasing_fillcolor='#00CC96'  
                    ))
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['5MA'], mode='lines', name='5MA (週線)', line=dict(color='#1E90FF', width=1.5)))
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['10MA'], mode='lines', name='10MA (雙週線)', line=dict(color='#FFD700', width=1.5)))
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['20MA'], mode='lines', name='20MA (月線)', line=dict(color='#9B59B6', width=2)))
                    
                    fig.update_layout(height=450, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 繪製副圖 (MACD)
                    st.markdown("##### 📉 MACD 波段動能")
                    fig_macd = go.Figure()
                    # 判斷 MACD 柱狀圖顏色 (大於0為紅，小於0為綠)
                    colors = ['#FF4B4B' if val > 0 else '#00CC96' for val in hist['Hist']]
                    fig_macd.add_trace(go.Bar(x=hist.index, y=hist['Hist'], marker_color=colors, name='MACD 柱狀體'))
                    fig_macd.add_trace(go.Scatter(x=hist.index, y=hist['MACD'], mode='lines', name='MACD (快線)', line=dict(color='#1E90FF', width=1.5)))
                    fig_macd.add_trace(go.Scatter(x=hist.index, y=hist['Signal'], mode='lines', name='Signal (慢線)', line=dict(color='#FFD700', width=1.5)))
                    fig_macd.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), template="plotly_dark")
                    st.plotly_chart(fig_macd, use_container_width=True)
                    
                    # 趨勢判定
                    curr_c = hist['Close'].iloc[-1]
                    ma5, ma10, ma20 = hist['5MA'].iloc[-1], hist['10MA'].iloc[-1], hist['20MA'].iloc[-1]
                    
                    if curr_c > ma5 > ma10 > ma20:
                        st.success("🟢 **波段多頭排列**：股價站上所有均線，且均線向上發散，是持股抱牢或逢回加碼的最佳型態！")
                    elif curr_c < ma20:
                        st.error("🔴 **波段空頭格局**：股價跌破月線 (20MA)，趨勢轉弱，波段操作者應嚴格執行停損或觀望。")
                    else:
                        st.warning("🟡 **波段整理中**：股價在均線間震盪，等待帶量突破表態。")
            except:
                st.error("無法取得圖表資料。")

# ==========================================
# 分頁 3：翻倍進度與日誌 (保留最受歡迎功能)
# ==========================================
with tab3:
    st.markdown("### 🏆 3千 ➔ 50萬 翻倍進度表")
    LOG_FILE = "swing_trade_log.csv"
    if os.path.exists(LOG_FILE):
        df_log = pd.read_csv(LOG_FILE)
    else:
        df_log = pd.DataFrame({"日期": [datetime.now(tw_tz).strftime('%Y-%m-%d')], "投入金額": [3000.0], "波段損益": [0.0], "備註": ["初始資金"]})

    total_pnl = df_log["波段損益"].sum()
    current_capital = 3000 + total_pnl
    target = 500000
    progress = min(current_capital / target, 1.0)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("目前總資金", f"${current_capital:,.0f}")
    c2.metric("波段累計損益", f"${total_pnl:,.0f}", f"{(total_pnl/3000)*100:.1f}% 總報酬")
    c3.metric("距離目標還差", f"${(target - current_capital):,.0f}")
    
    st.progress(progress)
    
    st.markdown("#### 📝 填寫波段平倉紀錄")
    edited_df = st.data_editor(
        df_log, num_rows="dynamic",
        column_config={
            "日期": st.column_config.TextColumn("平倉日期", required=True),
            "投入金額": st.column_config.NumberColumn("該筆買進成本 ($)", min_value=0, format="%d"),
            "波段損益": st.column_config.NumberColumn("平倉淨利 ($)", format="%d"),
            "備註": st.column_config.TextColumn("標的與心得")
        }, use_container_width=True
    )
    
    if not edited_df.equals(df_log):
        edited_df.to_csv(LOG_FILE, index=False)
        st.success("✅ 紀錄已更新！")
        st.rerun() 
        
    if len(edited_df) > 0:
        edited_df['累計資金'] = 3000 + edited_df['波段損益'].cumsum()
        fig = px.line(edited_df, x='日期', y='累計資金', markers=True, title="波段資產雪球軌跡")
        fig.update_layout(template="plotly_dark", yaxis_title="總資金 ($)", xaxis_title="日期")
        st.plotly_chart(fig, use_container_width=True)
