import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 網頁基本設定 (手機最佳化)
st.set_page_config(page_title="行動版股市助理", page_icon="📱", layout="centered")
st.title("📱 股市隨身助理")

# 取得台灣當前時間
tw_tz = pytz.timezone('Asia/Taipei')
current_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M')
st.caption(f"⏱️ 系統更新時間：{current_time}")

# --- 建立手機版雙分頁 ---
tab1, tab2 = st.tabs(["📊 個人持股試算", "🔥 今日 AI 推薦清單"])

# ==========================================
# 分頁 1：個人持股試算與走勢圖
# ==========================================
with tab1:
    st.markdown("### ⚙️ 輸入您的交易紀錄")
    
    # 針對手機螢幕將輸入框並排
    col_in1, col_in2 = st.columns(2)
    ticker = col_in1.text_input("股票代號 (如 2330.TW)", value="2330.TW")
    buy_price = col_in2.number_input("購買價格", min_value=0.0, value=500.0, step=1.0)
    
    col_in3, col_in4 = st.columns(2)
    buy_lots = col_in3.number_input("購買張數 (1張=1000股)", min_value=0, value=1, step=1)
    buy_odd_shares = col_in4.number_input("零股", min_value=0, value=0, step=1)

    total_shares = (buy_lots * 1000) + buy_odd_shares
    total_cost = buy_price * total_shares

    if st.button("🔄 刷新即時報價", key="refresh_btn"):
        st.cache_data.clear()

    @st.cache_data(ttl=60)
    def get_stock_data(ticker_symbol):
        stock = yf.Ticker(ticker_symbol)
        hist = stock.history(period="6mo")
        return stock.info, hist

    if ticker:
        try:
            info, hist_data = get_stock_data(ticker)
            current_price = info.get('currentPrice', info.get('regularMarketPrice', hist_data['Close'].iloc[-1]))
            
            current_value = current_price * total_shares
            profit_loss = current_value - total_cost
            roi = (profit_loss / total_cost) * 100 if total_cost > 0 else 0

            # 投資損益看板
            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.metric("即時股價", f"${current_price:,.2f}")
            c2.metric("總投資成本", f"${total_cost:,.0f}")
            
            c3, c4 = st.columns(2)
            c3.metric("目前總市值", f"${current_value:,.0f}")
            c4.metric("即時損益", f"${profit_loss:,.0f}", f"{roi:.2f}%", delta_color="normal" if profit_loss >= 0 else "inverse")

            # 技術分析與操作建議
            st.markdown("### 💡 個股走勢與操作建議")
            hist_data['MA10'] = hist_data['Close'].rolling(window=10).mean()
            hist_data['MA20'] = hist_data['Close'].rolling(window=20).mean()
            
            delta = hist_data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            hist_data['RSI'] = 100 - (100 / (1 + rs))

            latest_rsi = hist_data['RSI'].iloc[-1]
            ma10 = hist_data['MA10'].iloc[-1]
            ma20 = hist_data['MA20'].iloc[-1]
            
            if latest_rsi <= 30:
                st.success("**🟢 建議買入 (跌深反彈)**\nRSI顯示超賣，極大機率出現反彈。")
            elif ma10 > ma20 and latest_rsi < 65:
                st.success("**🟢 建議買入 (順勢操作)**\n均線多頭排列且未過熱，適合順勢買進。")
            elif latest_rsi >= 75:
                st.error("**🔴 建議賣出 / 獲利了結**\nRSI顯示極度過熱，有回檔修正風險。")
            elif ma10 < ma20 and latest_rsi > 40:
                st.warning("**🟡 建議觀察 (趨勢偏弱)**\n空頭排列且未達超賣區間，先觀望等待底部。")
            else:
                st.info("**🟡 建議觀察 (區間震盪)**\n技術面訊號不明確，處於整理階段。")

            # 繪圖
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=hist_data.index, open=hist_data['Open'], high=hist_data['High'], low=hist_data['Low'], close=hist_data['Close'], name='K線'))
            fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA10'], mode='lines', name='10日均線', line=dict(color='blue', width=1)))
            fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA20'], mode='lines', name='20日均線', line=dict(color='orange', width=1)))
            
            if total_cost > 0:
                fig.add_hline(y=buy_price, line_dash="dash", line_color="red", annotation_text="成本價")
            
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), xaxis_rangeslider_visible=False, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error("無法取得資料，請確認股票代號。")

# ==========================================
# 分頁 2：今日 AI 自動掃描推薦
# ==========================================
with tab2:
    st.markdown("### 🤖 盤面自動掃描雷達")
    st.caption("系統每日自動追蹤熱門權值股與 ETF，篩選出符合買進訊號的潛力標的。")

    # 內建追蹤名單與公司簡介
    watch_pool = {
        "2330.TW": "台灣積體電路 (全球晶圓代工龍頭，護國神山)",
        "2317.TW": "鴻海精密 (全球最大電子代工廠，蘋概股指標)",
        "2454.TW": "聯發科 (全球知名IC設計大廠，手機晶片巨頭)",
        "2308.TW": "台達電 (全球電源管理與散熱解決方案龍頭)",
        "2881.TW": "富邦金 (台灣大型金融控股，獲利資優生)",
        "0050.TW": "元大台灣50 ETF (一次買進台股市值前50大企業)"
    }

    @st.cache_data(ttl=3600)
    def scan_market(pool):
        recommended = []
        for sym, desc in pool.items():
            try:
                stock = yf.Ticker(sym)
                hist = stock.history(period="3mo")
                if len(hist) < 20: continue
                
                hist['MA10'] = hist['Close'].rolling(10).mean()
                hist['MA20'] = hist['Close'].rolling(20).mean()
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                hist['RSI'] = 100 - (100 / (1 + rs))
                
                last_close = hist['Close'].iloc[-1]
                last_ma10 = hist['MA10'].iloc[-1]
                last_ma20 = hist['MA20'].iloc[-1]
                last_rsi = hist['RSI'].iloc[-1]
                
                reason = ""
                if last_rsi <= 30:
                    reason = "跌深反彈 (RSI超賣，反彈契機大)"
                elif last_ma10 > last_ma20 and last_rsi < 65:
                    reason = "順勢多頭 (均線偏多，尚未過熱)"
                    
                if reason:
                    recommended.append({
                        "symbol": sym,
                        "price": last_close,
                        "desc": desc,
                        "reason": reason,
                        "rsi": last_rsi
                    })
            except Exception:
                pass
        return recommended

    with st.spinner('AI 正在全網掃描最新數據，請稍候...'):
        recs = scan_market(watch_pool)

    if recs:
        st.success(f"🎉 掃描完成！今日共有 **{len(recs)}** 檔標的符合買進訊號：")
        for r in recs:
            with st.expander(f"📌 {r['symbol']} - 點我看詳情"):
                st.write(f"**📝 公司簡介**：{r['desc']}")
                st.write(f"**💲 最新股價**：${r['price']:.2f}")
                st.write(f"**🔥 推薦理由**：{r['reason']}")
                st.write(f"**📊 RSI 數值**：{r['rsi']:.1f}")
                st.info("💡 提示：您可以記下代號，到左側「個人持股試算」查看詳細 K 線圖。")
    else:
        st.warning("👀 盤面掃描完成：目前追蹤名單內**無強烈買進訊號**。建議保留現金，耐心等待更好時機！")
