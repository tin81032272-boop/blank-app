import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os

# =====================================================
# 頁面設定與自訂 CSS
# =====================================================
st.set_page_config(page_title="存股指揮中心 Pro", page_icon="🌱", layout="wide")

st.markdown("""
<style>
    .big-font { font-size:22px !important; font-weight: bold; color: #2E86C1; }
    .metric-box { background-color: #f0f8ff; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #dcdcdc;}
    .card { background-color: #ffffff; color: #333; padding: 18px; border-radius: 12px; border-left: 6px solid #27AE60; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);}
    .badge-green { background-color: #27AE60; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 置頂控制區與目標設定
# =====================================================
st.title("🌱 財富雪球：存股指揮中心")

# 設定存股長期目標 (調整為 150 萬)
TARGET_AMOUNT = 1500000 

stock_pool = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "0050.TW": "元大台灣50", 
    "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00919.TW": "群益台灣精選高息",
    "00935.TW": "野村臺灣新科技50", "00910.TW": "第一金太空衛星", "2881.TW": "富邦金",
    "NVDA": "輝達"
}

tab1, tab2, tab3, tab4 = st.tabs(["📊 庫存與 150 萬目標", "💰 每月資金配置 (Total Intake)", "📈 標的健康度 (撿便宜雷達)", "💵 股息記帳本"])

# =====================================================
# TAB 1: 庫存總覽與 150 萬進度條 + 達標試算
# =====================================================
with tab1:
    st.markdown("### 🏦 目前庫存與資產總值")
    
    INV_FILE = "portfolio.csv"
    if os.path.exists(INV_FILE): 
        df_inv = pd.read_csv(INV_FILE)
    else: 
        df_inv = pd.DataFrame({"代號":["2330.TW", "00935.TW"], "股數":[100, 1000], "平均成本":[800.0, 15.0]})

    st.write("✏️ **編輯你的庫存資料 (系統會自動抓取即時股價計算)**")
    edited_inv = st.data_editor(df_inv, num_rows="dynamic", use_container_width=True)
    if not edited_inv.equals(df_inv):
        edited_inv.to_csv(INV_FILE, index=False)
        st.success("✅ 庫存已更新！")

    total_assets = 0
    portfolio_data = []
    
    with st.spinner("正在結算總資產與即時股價..."):
        for index, row in edited_inv.iterrows():
            sym = row["代號"]
            shares = row["股數"]
            cost = row["平均成本"]
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="5d")
                current_price = hist['Close'].iloc[-1] if not hist.empty else cost
            except:
                current_price = cost
                
            market_value = current_price * shares
            cost_value = cost * shares
            pnl = market_value - cost_value
            pnl_pct = (pnl / cost_value * 100) if cost_value > 0 else 0
            
            total_assets += market_value
            portfolio_data.append({
                "標的": stock_pool.get(sym, sym), "現價": current_price, 
                "總市值": market_value, "未實現損益": pnl, "報酬率(%)": pnl_pct
            })

    # 150 萬目標進度
    progress_pct = min(total_assets / TARGET_AMOUNT, 1.0)
    
    st.markdown("---")
    st.markdown(f"### 🎯 邁向 150 萬財務目標進度：{progress_pct*100:.1f}%")
    st.progress(progress_pct)
    
    colA, colB, colC = st.columns(3)
    colA.metric("目前總資產 (NTD)", f"${total_assets:,.0f}")
    colB.metric("距離目標還差 (NTD)", f"${max(TARGET_AMOUNT - total_assets, 0):,.0f}")
    
    total_cost = sum(r["平均成本"] * r["股數"] for _, r in edited_inv.iterrows())
    total_pnl = total_assets - total_cost
    colC.metric("總未實現損益", f"${total_pnl:,.0f}", f"{(total_pnl/total_cost*100) if total_cost>0 else 0:.2f}%")

    # 新增：達標時間試算器
    st.markdown("#### ⏱️ 預估達標時間試算")
    with st.expander("點擊展開試算器", expanded=True):
        sc1, sc2, sc3 = st.columns(3)
        monthly_invest = sc1.number_input("預計每月再投入 (元)", value=10000, step=1000)
        expected_cagr = sc2.slider("預期年化報酬率 (%)", 3, 15, 7)
        
        if monthly_invest > 0:
            # 使用期末終值公式 (FV) 概算期數
            r_monthly = expected_cagr / 100 / 12
            target_remaining = max(TARGET_AMOUNT - total_assets, 0)
            if target_remaining == 0:
                st.success("🎉 你已經達成 150 萬的目標了！")
            else:
                # 計算需要幾個月
                months_needed = np.nper(r_monthly, -monthly_invest, -total_assets, TARGET_AMOUNT)
                years_needed = months_needed / 12
                sc3.metric("預估還需時間", f"{years_needed:.1f} 年")
                st.info(f"💡 保持每月投入 {monthly_invest:,} 元，並維持 {expected_cagr}% 的年化報酬率，預計約 {years_needed:.1f} 年後總資產將突破 150 萬。")

    if portfolio_data:
        df_port = pd.DataFrame(portfolio_data)
        fig_pie = px.pie(df_port, values='總市值', names='標的', title="資產配置佔比 (風險分散檢查)", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

# =====================================================
# TAB 2: 每月投入配置 (Total Intake)
# =====================================================
with tab2:
    st.markdown("### 📋 每月定期定額預算分配表")
    st.write("設定你的核心與衛星持股比例，系統會自動幫你計算各種每月總投入額度的分配金額。")
    
    c1, c2, c3 = st.columns(3)
    stock1 = c1.text_input("主力標的 1", value="輝達 (NVDA)")
    weight1 = c1.number_input("權重 (%) ", value=40, step=5, key="w1")
    
    stock2 = c2.text_input("主力標的 2", value="野村臺灣新科技50 (00935)")
    weight2 = c2.number_input("權重 (%)", value=40, step=5, key="w2")
    
    stock3 = c3.text_input("輔助衛星標的", value="第一金太空衛星 (00910)")
    weight3 = c3.number_input("權重 (%)  ", value=20, step=5, key="w3")

    if weight1 + weight2 + weight3 != 100:
        st.error("⚠️ 權重總和必須為 100%！請調整上方數值。")
    else:
        # 使用你最熟悉的 Total Intake 表格格式
        table_md = f"""
| 每月總投入 (Total Intake) | {stock1} <br> 配置 ({weight1}%) | {stock2} <br> 配置 ({weight2}%) | {stock3} <br> 配置 ({weight3}%) |
| :--- | :--- | :--- | :--- |
"""
        for intake in [3000, 5000, 10000, 15000, 20000]:
            table_md += f"| **{intake:,} 元** | {intake * weight1 / 100:,.0f} 元 | {intake * weight2 / 100:,.0f} 元 | {intake * weight3 / 100:,.0f} 元 |\n"
        
        st.markdown(table_md, unsafe_allow_html=True)
        st.info("💡 **操作建議**：將此表對應的金額設定於券商的「定期定額」或「碎股/零股」自動扣款，發薪日隔天自動執行，克服人性弱點。")

# =====================================================
# TAB 3: 標的健康度 (長線撿便宜雷達)
# =====================================================
with tab3:
    st.markdown("### 📈 存股標的健康檢查 (日K與年線)")
    st.write("當好公司的股價跌到年線以下，通常是長線累積股數的好時機。")
    
    chk_sym = st.selectbox("選擇要檢查的標的", list(stock_pool.keys()), format_func=lambda x: f"{x} {stock_pool[x]}")
    
    if st.button("🔍 檢查體質與位階"):
        with st.spinner("抓取近一年歷史資料中..."):
            ticker = yf.Ticker(chk_sym)
            hist = ticker.history(period="1y")
            
            if not hist.empty:
                hist['60MA'] = hist['Close'].rolling(window=60).mean()
                hist['240MA'] = hist['Close'].rolling(window=240, min_periods=100).mean()
                
                curr_price = hist['Close'].iloc[-1]
                ma240 = hist['240MA'].iloc[-1]
                high_52w = hist['High'].max()
                drop_from_high = (curr_price - high_52w) / high_52w * 100
                
                if pd.notna(ma240) and ma240 > 0:
                    bias = (curr_price - ma240) / ma240 * 100
                    if bias > 20: status = "🔴 股價高於年線過多 (維持定期定額，不建議單筆重壓)"
                    elif bias < 0: status = "🟢 股價低於年線 (長線保護短線，可能是加碼好時機)"
                    else: status = "🟡 股價在合理均值附近 (適合持續買進)"
                else:
                    bias = 0
                    status = "資料不足無法計算年線"
                
                st.markdown(f"""
                <div class="card">
                    <h4>{stock_pool[chk_sym]} 存股數據</h4>
                    <ul>
                        <li><b>即時現價：</b> ${curr_price:.2f}</li>
                        <li><b>距離 52 週高點：</b> 跌幅 {drop_from_high:.2f}% (從最高點 ${high_52w:.2f} 回落)</li>
                        <li><b>年線 (240MA) 乖離率：</b> {bias:.2f}% 👉 <b>{status}</b></li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='收盤價', line=dict(color='#2E86C1')))
                fig.add_trace(go.Scatter(x=hist.index, y=hist['60MA'], name='季線 (60MA)', line=dict(color='#F39C12', dash='dot')))
                fig.add_trace(go.Scatter(x=hist.index, y=hist['240MA'], name='年線 (240MA)', line=dict(color='#27AE60', width=2)))
                
                fig.update_layout(height=400, template="plotly_white", hovermode="x unified", title=f"{stock_pool[chk_sym]} 近一年走勢")
                st.plotly_chart(fig, use_container_width=True)

# =====================================================
# TAB 4: 股息記帳本
# =====================================================
with tab4:
    st.markdown("### 💵 股息複利紀錄")
    st.write("將領到的股息記錄下來，並提醒自己**將股息再投資買入零股**，啟動複利效應！")
    
    DIV_FILE = "dividend_log.csv"
    if os.path.exists(DIV_FILE): 
        df_div = pd.read_csv(DIV_FILE)
    else: 
        df_div = pd.DataFrame({"發放日期":[datetime.now().strftime('%Y-%m-%d')], "標的":["00935.TW"], "發放總金(NTD)":[0], "是否已再投資":[False]})

    edited_div = st.data_editor(df_div, num_rows="dynamic", use_container_width=True)
    if not edited_div.equals(df_div):
        edited_div.to_csv(DIV_FILE, index=False)
        st.success("✅ 股息紀錄已儲存！")
    
    total_div = edited_div["發放總金(NTD)"].sum()
    st.metric("累計已領取總股息", f"NT$ {total_div:,.0f}")
    
    if len(edited_div) > 1 and total_div > 0:
        fig_div = px.bar(edited_div, x='發放日期', y='發放總金(NTD)', color='標的', title="股息現金流紀錄")
        st.plotly_chart(fig_div, use_container_width=True)
