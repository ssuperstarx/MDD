import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. 웹 페이지 기본 설정 (넓은 화면 사용)
st.set_page_config(page_title="미국 주요 ETF 하락장 대시보드", page_icon="📊", layout="wide")

st.title("📊 미국 주요 ETF 하락장 모니터링")
st.markdown("현재 시장이 역사적 고점 대비 얼마나 하락했는지, 언제 물타기를 해야 할지 실시간으로 확인하세요.")

tickers = ["QQQ", "SPY", "IWM", "HYG", "LQD", "XLY", "XLP"]
ticker_themes = {
    "QQQ": "나스닥 100 (기술주)", "SPY": "S&P 500 (대형주)", "IWM": "러셀 2000 (중소형주)",
    "HYG": "하이일드 회사채", "LQD": "투자등급 회사채", "XLY": "경기소비재", "XLP": "필수소비재"
}

# 2. 데이터 캐싱 (매번 접속할 때마다 새로고침되는 것을 방지하여 속도 향상)
@st.cache_data(ttl=3600) # 1시간(3600초) 동안 데이터 유지
def load_data():
    end_date = datetime.today()
    start_date = end_date - relativedelta(years=20)
    df = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        return df['Close']
    return df['Close']

with st.spinner('실시간 주가 데이터를 불러오는 중입니다...'):
    close_prices = load_data()

st.success(f"데이터 업데이트 완료! (기준일: {close_prices.index[-1].strftime('%Y-%m-%d')})")

# 3. 화면 그리드(바둑판) 설정
cols = st.columns(3) # 3열로 배치

for i, ticker in enumerate(tickers):
    prices = close_prices[ticker].dropna()
    
    # 분석 로직
    roll_max_20y = prices.cummax()
    drawdown_20y = (prices / roll_max_20y - 1.0) * 100
    mdd_20y = drawdown_20y.min()
    current_dd_20y = drawdown_20y.iloc[-1]
    
    is_peak = prices == roll_max_20y
    peak_dates = prices[is_peak].index
    last_peak = peak_dates[-1] if len(peak_dates) > 0 else prices.index[0]
    ongoing_days = (prices.index[-1] - last_peak).days
    
    if current_dd_20y <= -20.0:
        status, color = "🔴 물타기 구간 (적극 매수)", "red"
    elif current_dd_20y <= -10.0:
        status, color = "🟡 조정 구간 (분할 매수)", "orange"
    else:
        status, color = "🔵 안정 구간 (적립 유지)", "blue"

    # 웹 화면에 카드 형태로 데이터 출력
    with cols[i % 3]: # 3개의 컬럼에 순서대로 배치
        st.subheader(f"{ticker} - {ticker_themes[ticker]}")
        st.markdown(f"**상태:** :{color}[{status}]")
        
        # 핵심 지표 (Metric) 위젯 사용
        if current_dd_20y == 0:
            st.metric(label="현재 하락률", value="✨ 전고점 갱신 중!")
        else:
            st.metric(label=f"현재 하락률 (마지막 고점: {last_peak.strftime('%y.%m.%d')} / {ongoing_days}일째)", 
                      value=f"{current_dd_20y:.2f}%")
            
        st.caption(f"역대 최대 낙폭(MDD): {mdd_20y:.2f}%")
        
        # 차트 그리기
        fig, ax = plt.subplots(figsize=(5, 2.5))
        ax.plot(drawdown_20y.index, drawdown_20y, color='red', alpha=0.8, linewidth=1)
        ax.fill_between(drawdown_20y.index, drawdown_20y, 0, color='red', alpha=0.2)
        ax.axhline(0, color='black', linewidth=0.8)
        ax.axhline(-20, color='blue', linestyle=':', linewidth=1.5)
        ax.set_ylabel("Drawdown (%)", fontsize=8)
        ax.tick_params(axis='both', which='major', labelsize=8)
        ax.grid(True, linestyle='--', alpha=0.3)
        st.pyplot(fig)
        
        st.divider() # 카드 구분선