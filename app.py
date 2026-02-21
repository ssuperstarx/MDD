import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ============================================================
# 1. 페이지 및 기본 설정 (변경 금지 구역)
# ============================================================
st.set_page_config(page_title="종합 투자 대시보드", page_icon="📊", layout="wide")
st.title("📊 통합 투자 대시보드")
st.markdown("MDD 기반의 하락장 모니터링, RAI 지표 기반의 리밸런싱, DCA 백테스팅을 확인하세요.")

# --- [추가/수정] 새로운 자산(원자재, 반도체 지수, 암호화폐) 티커 반영 ---
tickers_mdd = [
    "QQQ", "SPY", "IWM", "HYG", "LQD", "XLY", "XLP", "MAGS", "QLD", "GLD", "SLV",
    "SOXX", "BTC-USD", "ETH-USD", "SOL-USD" # 신규 추가 티커 4종
]
tickers_rebal = ["SPY", "QQQ", "IWM", "HYG", "LQD", "XLY", "XLP", "^VIX", "^VIX3M", "SHY"]
all_tickers = list(set(tickers_mdd + tickers_rebal))

ticker_themes = {
    "QQQ": "나스닥 100", "SPY": "S&P 500", "IWM": "러셀 2000",
    "HYG": "하이일드 채권", "LQD": "투자등급 채권", "XLY": "경기소비재", "XLP": "필수소비재",
    "MAGS": "매그니피센트 7", "QLD": "나스닥 100 (2배)", "GLD": "금 (Gold)", "SLV": "은 (Silver)", 
    "SOXX": "반도체 지수", "BTC-USD": "비트코인 (BTC)", "ETH-USD": "이더리움 (ETH)", "SOL-USD": "솔라나 (SOL)",
    "^VIX": "변동성 지수 (VIX)", "^VIX3M": "VIX 3개월", "SHY": "단기 국채 (1-3년)"
}

# ============================================================
# 2. 전역 데이터 로드 (1, 2페이지용)
# ============================================================
@st.cache_data(ttl=900)
def load_data(tickers, years=20):
    end_date = datetime.today()
    start_date = end_date - relativedelta(years=years)
    df = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
    return df

# ============================================================
# 3. 화면 분할 (Sidebar Navigation)
# ============================================================
st.sidebar.header("메뉴 선택")
page = st.sidebar.radio(
    "페이지 선택", 
    [
        "📊 1. ETF 하락장 모니터링 (MDD)", 
        "🔄 2. 포트폴리오 리밸런싱 시그널 (RAI)",
        "📈 3. DCA 백테스팅 시뮬레이터" # 신규 페이지 추가
    ],
    index=0,
    label_visibility="collapsed",
    key="main_navigation"
)

st.sidebar.markdown("---")
st.sidebar.header("데이터 설정")
lookback_years = st.sidebar.slider("과거 데이터 조회 기간 (년)", min_value=1, max_value=30, value=20)

with st.spinner(f'최근 {lookback_years}년의 주가 데이터를 불러오는 중입니다...'):
    df_raw = load_data(all_tickers, lookback_years)

if isinstance(df_raw.columns, pd.MultiIndex):
    close_prices = df_raw['Close']
    high_prices = df_raw['High']
    low_prices = df_raw['Low']
else:
    close_prices = df_raw
    high_prices = df_raw
    low_prices = df_raw

# ------------------------------------------------------------
# [PAGE 1] 기존 ETF 대시보드
# ------------------------------------------------------------
if page == "📊 1. ETF 하락장 모니터링 (MDD)":
    st.header("📊 1. ETF 하락장 모니터링 (MDD)")
    st.info(f"📅 **조회 기간:** 최근 {lookback_years}년 (시작: {(datetime.today() - relativedelta(years=lookback_years)).strftime('%Y-%m-%d')})")
    
    st.markdown("""
    ### 🔔 상태 판별 기준 (MDD)
    | 상태 | 상세 기준 | 투자전략 |
    | :--- | :--- | :--- |
    | 🔴 **물타기 구간** | **MDD -20% 이하** | 적극 매수 및 비중 확대 |
    | 🟡 **조정 구간** | **MDD -10% 이하** | 분할 매수 진입 |
    | 🔵 **안정 구간** | **MDD -10% 초과** | 기존 적립 및 관망 유지 |
    """)
    st.markdown("---")
    
    # 3개씩 묶어서 행(Row) 단위로 컬럼 생성
    for i in range(0, len(tickers_mdd), 3):
        cols = st.columns(3) 
        
        for j in range(3):
            if i + j < len(tickers_mdd):
                ticker = tickers_mdd[i + j]
                prices = close_prices[ticker].dropna()
                if prices.empty: continue
                
                roll_max = prices.cummax()
                drawdown = (prices / roll_max - 1.0) * 100
                mdd_val = drawdown.min()
                current_dd = drawdown.iloc[-1]
                
                is_peak = prices == roll_max
                last_peak_dt = prices[is_peak].index[-1]
                ongoing_days = (prices.index[-1] - last_peak_dt).days
                
                if current_dd <= -20.0:
                    status, color = "🔴 물타기 구간 (적극 매수)", "red"
                elif current_dd <= -10.0:
                    status, color = "🟡 조정 구간 (분할 매수)", "orange"
                else:
                    status, color = "🔵 안정 구간 (적립 유지)", "blue"

                with cols[j]:
                    st.subheader(f"{ticker} - {ticker_themes[ticker]}")
                    current_price = prices.iloc[-1]
                    prev_price = prices.iloc[-2] if len(prices) > 1 else current_price
                    daily_return = (current_price / prev_price - 1) * 100
                    return_color = "red" if daily_return > 0 else "blue" if daily_return < 0 else "gray"
                    
                    st.markdown(f"**상태:** :{color}[{status}]")
                    st.markdown(f"**현재가:** ${current_price:,.2f} (:{return_color}[{daily_return:+.2f}%])")
                    
                    if current_dd == 0:
                        st.markdown(f"""
                            <div style="font-size:14px; color:gray; margin-bottom:2px;">현재 하락률</div>
                            <div style="font-size:20px; font-weight:bold;">✨ 전고점 갱신 중!</div>
                        """, unsafe_allow_html=True)
                    else:
                        label_text = f"현재 하락률 (고점: {last_peak_dt.strftime('%y.%m.%d')} / {ongoing_days}일째)"
                        st.markdown(f"""
                            <div style="font-size:14px; color:gray; margin-bottom:2px;">{label_text}</div>
                            <div style="font-size:20px; font-weight:bold; color:{color};">{current_dd:.2f}%</div>
                        """, unsafe_allow_html=True)
                    
                    fig, ax = plt.subplots(figsize=(5, 3))
                    ax.plot(drawdown.index, drawdown, color='red', alpha=0.8, linewidth=1)
                    ax.fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.2)
                    ax.axhline(0, color='black', linewidth=0.8)
                    ax.axhline(-20, color='blue', linestyle=':', label='-20% 기준선')
                    ax.set_ylabel("Drawdown (%)", fontsize=8)
                    ax.grid(True, linestyle='--', alpha=0.3)
                    st.pyplot(fig)
                    st.markdown("---")

# ------------------------------------------------------------
# [PAGE 2] RAI 기반 동적 리밸런싱
# ------------------------------------------------------------
elif page == "🔄 2. 포트폴리오 리밸런싱 시그널 (RAI)":
    st.header("🔄 2. 포트폴리오 리밸런싱 시그널 (RAI)")
    st.markdown("### ⚙️ 리밸런싱 파라미터 및 성향 설정")
    
    col1, col2, col3, col4 = st.columns(4)
    port_val = col1.number_input("현재 포트폴리오 금액 ($)", min_value=100, value=10000, step=100)
    cur_q_weight = col2.number_input("현재 QQQ 비중 (0.0~1.0)", min_value=0.0, max_value=1.0, value=0.70, step=0.05)
    rebal_freq = col3.selectbox("리밸런싱 기준일", ["D (매일)", "W-FRI (주 1회 금요일)", "M (월말)"])
    rebal_freq_val = rebal_freq.split(" ")[0]
    
    strategy = col4.selectbox(
        "💡 투자 성향 조절", 
        ["🛡️ 방어형 (하락 시 현금 80%)", "⚖️ 중립형 (기본, 하락 시 현금 60%)", "🔥 공격형 (하락 시 현금 40%)"], 
        index=1
    )

    W_FULL = pd.Series({
        "vix_level": 0.0087, "small_big": 0.0079, "realized_vol20": 0.0033,
        "cyc_def": 0.0023, "adx14": 0.0007, "vix_term": -0.0044,
        "credit_risk": -0.0147, "trend_200": -0.0162
    })
    DIRECTION = {
        "vix_level": -1, "vix_term": -1, "realized_vol20": -1, "credit_risk": +1,
        "cyc_def": +1, "small_big": +1, "trend_200": +1, "adx14": +1
    }

    def quantile_to_weight(q: float, strat: str) -> float:
        if "방어형" in strat:
            if q <= 0.10: return 0.20
            elif q <= 0.25: return 0.40
            elif q <= 0.50: return 0.60
            elif q <= 0.75: return 0.80
            else: return 1.00
        elif "공격형" in strat:
            if q <= 0.10: return 0.60
            elif q <= 0.25: return 0.70
            elif q <= 0.50: return 0.80
            elif q <= 0.75: return 0.90
            else: return 1.00
        else: 
            if q <= 0.10: return 0.40
            elif q <= 0.25: return 0.55
            elif q <= 0.50: return 0.70
            elif q <= 0.75: return 0.85
            else: return 1.00

    def is_exec_day(dt: pd.Timestamp, all_days: pd.DatetimeIndex, freq: str) -> bool:
        if freq == "D": return True
        if freq == "W-FRI": return dt.weekday() == 4
        if freq == "M":
            month_days = all_days[all_days.to_period("M") == dt.to_period("M")]
            return dt == month_days.max()
        return False

    spy_c = close_prices["SPY"].dropna()
    spy_h = high_prices["SPY"].reindex(spy_c.index)
    spy_l = low_prices["SPY"].reindex(spy_c.index)
    
    qqq_c = close_prices["QQQ"].reindex(spy_c.index).ffill()
    iwn_c = close_prices["IWM"].reindex(spy_c.index).ffill()
    hyg_c = close_prices["HYG"].reindex(spy_c.index).ffill()
    lqd_c = close_prices["LQD"].reindex(spy_c.index).ffill()
    xly_c = close_prices["XLY"].reindex(spy_c.index).ffill()
    xlp_c = close_prices["XLP"].reindex(spy_c.index).ffill()
    vix_c = close_prices["^VIX"].reindex(spy_c.index).ffill()
    vix3m = close_prices["^VIX3M"].reindex(spy_c.index).ffill()

    feat = pd.DataFrame(index=spy_c.index)
    feat["vix_level"] = vix_c
    feat["vix_term"] = vix_c / vix3m
    feat["realized_vol20"] = spy_c.pct_change().rolling(20).std(ddof=0) * np.sqrt(252)
    feat["credit_risk"] = hyg_c / lqd_c
    feat["cyc_def"] = xly_c / xlp_c
    feat["small_big"] = iwn_c / spy_c
    feat["trend_200"] = spy_c / spy_c.rolling(200).mean() - 1.0

    up_move = spy_h.diff()
    down_move = -spy_l.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr1 = spy_h - spy_l
    tr2 = (spy_h - spy_c.shift()).abs()
    tr3 = (spy_l - spy_c.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    plus_di = 100 * pd.Series(plus_dm, index=spy_c.index).rolling(14).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=spy_c.index).rolling(14).mean() / atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).replace([np.inf, -np.inf], np.nan)
    feat["adx14"] = dx.rolling(14).mean()

    Xz = pd.DataFrame(index=feat.index)
    for c in feat.columns:
        s = DIRECTION[c] * feat[c]
        m = s.rolling(252).mean()
        sd = s.rolling(252).std(ddof=0)
        Xz[c] = (s - m) / sd

    days_all = qqq_c.dropna().index
    latest_dt = days_all[-1]

    rai_vals, used_vals = [], []
    for dt in days_all:
        if dt in Xz.index:
            avail = [f for f in W_FULL.index if pd.notna(Xz.loc[dt, f])]
        else:
            avail = []
        
        if len(avail) < 4:
            rai_vals.append(np.nan)
        else:
            Wd = W_FULL[avail].copy()
            Wd *= (W_FULL.abs().sum() / Wd.abs().sum())
            rai_vals.append(float((Xz.loc[dt, avail] * Wd).sum()))
        used_vals.append(len(avail))

    rai = pd.Series(rai_vals, index=days_all, name="RAI")
    
    roll_win = int(252 * 2)
    q_exp = rai.expanding(min_periods=1).apply(lambda x: (x <= x[-1]).mean(), raw=True)
    q_roll = rai.rolling(roll_win).apply(lambda x: (x <= x[-1]).mean(), raw=True)
    q = q_roll.fillna(q_exp)
    
    target_w_series = q.apply(lambda x: quantile_to_weight(x, strategy))

    rai_today = rai.iloc[-1]
    q_today = q.iloc[-1]
    target_today = target_w_series.iloc[-1]
    is_today_exec = is_exec_day(latest_dt, days_all, rebal_freq_val)

    st.markdown("---")
    st.markdown(f"### 💡 오늘의 포지션 시그널 (기준일: {latest_dt.strftime('%Y-%m-%d')})")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("오늘의 RAI (위험선호도)", f"{rai_today:.3f}")
    c2.metric("RAI 백분위 (최근 2년 상대평가)", f"{q_today*100:.1f}%")
    c3.metric(f"목표 비중 ({strategy.split(' ')[1]})", f"{target_today*100:.0f}%", f"현재 {cur_q_weight*100:.0f}%")
    
    delta = target_today - cur_q_weight
    dollars = delta * port_val

    if not is_today_exec:
        c4.metric("오늘의 Action", "HOLD", "실행일 아님(보류)")
        st.info(f"선택하신 주기에 따르면 오늘은 리밸런싱 실행일이 아닙니다. 다음 **{rebal_freq_val}** 일정에 맞추어 아래 표적을 고려하세요.")
    else:
        if abs(delta) < 0.01:
            c4.metric("오늘의 Action", "HOLD", "목표 비중과 일치")
            st.success("✅ 이미 목표 비중에 도달해 있으므로 오늘은 매매할 필요가 없습니다.")
        elif delta > 0:
            c4.metric("오늘의 Action", "BUY (매수)", f"+${abs(dollars):,.0f}")
            st.error(f"📈 **비중 확대 신호:** 평가금액 기준 약 **${abs(dollars):,.0f}** 규모의 주식을 추가 매수하세요.")
        else:
            c4.metric("오늘의 Action", "SELL (매도)", f"-${abs(dollars):,.0f}")
            st.warning(f"📉 **비중 축소 신호:** 평가금액 기준 약 **${abs(dollars):,.0f}** 규모의 주식을 매도하여 현금을 확보하세요.")

    st.markdown("#### 📅 최근 20거래일 시그널 스냅샷")
    snap_days = days_all[-20:]
    snap_data = []
    temp_w = cur_q_weight
    
    for dt in snap_days:
        tw = target_w_series.loc[dt]
        exec_today = is_exec_day(dt, days_all, rebal_freq_val)
        diff = tw - temp_w
        
        if exec_today:
            if abs(diff) < 0.01: act_str = "HOLD"
            elif diff > 0: act_str = f"BUY (+{diff*100:.0f}%p)"
            else: act_str = f"SELL ({diff*100:.0f}%p)"
            temp_w = tw
        else:
            if abs(diff) < 0.01: act_str = "HOLD [Sched]"
            elif diff > 0: act_str = f"BUY (+{diff*100:.0f}%p) [Sched]"
            else: act_str = f"SELL ({diff*100:.0f}%p) [Sched]"

        snap_data.append({
            "날짜": dt.strftime('%Y-%m-%d'),
            "QQQ 종가": round(qqq_c.loc[dt], 2),
            "RAI 지수": round(rai.loc[dt], 3),
            "분위수": round(q.loc[dt], 3),
            "목표 비중": f"{tw*100:.0f}%",
            "액션": act_str
        })
    
    st.dataframe(pd.DataFrame(snap_data).set_index("날짜"), use_container_width=True)

    st.markdown("#### 📈 최근 1년 RAI 및 목표 비중 추이")
    plot_days = days_all[-252:]
    
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.caption("RAI (Risk Appetite Index) 추이")
        st.line_chart(rai.reindex(plot_days))
    with chart_col2:
        st.caption("자동 산출된 목표 비중 (%) 추이")
        st.line_chart(target_w_series.reindex(plot_days) * 100)

    st.markdown("---")
    st.markdown("### 🧠 AI 목표 비중(Target Weight) 산출 원리")
    st.markdown("""
    이 대시보드의 **리밸런싱 시그널**은 단순한 가격 하락이 아니라, 시장의 심리와 자금 흐름을 읽어내는 **5단계의 알고리즘**을 거쳐 오늘 포트폴리오의 최적 비중을 결정합니다.

    1. **8대 핵심 지표 수집**: 변동성(VIX 등 3개), 신용위험(회사채 비율), 기관 스마트머니 자금흐름(경기민감/방어주, 대/중소형주), 시장의 굵은 추세 강도(ADX) 등 거시경제를 파악하는 8가지 재료를 모읍니다.
    2. **Z-Score 표준화**: 수집된 재료들이 평소보다 얼마나 비정상적인지 파악하기 위해, 최근 1년(252일) 평균 대비 현재 값이 얼마나 벗어나 있는지(표준편차) 동일한 잣대로 맞춥니다.
    3. **RAI(위험 선호 지수) 산출**: 인공지능 기계학습(Ridge Regression)으로 과거 데이터를 분석해 찾아낸 **각 지표의 가중치**를 곱하고 더합니다. 이 과정을 통해 현재 시장의 투자 심리를 1개의 직관적인 점수(RAI)로 압축해 냅니다.
    4. **최근 2년 내 상대 순위(백분위) 평가**: 과거 10년 전의 낡은 데이터가 아니라, **최근 2년(약 500거래일) 동안의 분위기 속에서 오늘의 RAI 점수가 상위 몇 %에 위치하는지(백분위)**를 계산하여 단기 폭락/급등장에 유연하게 대처합니다.
    5. **목표 비중 매핑 (성향 반영)**: 산출된 백분위(%) 위치에 따라 포트폴리오 비중을 5단계로 조절합니다. 상단에서 설정하신 **[투자 성향]**에 따라 하락장(하위 10% 미만) 진입 시 방어 수준(안전자산 최대 확보량)이 다르게 맵핑됩니다.
    """)

# ------------------------------------------------------------
# [PAGE 3] DCA 백테스팅 시뮬레이터
# ------------------------------------------------------------
elif page == "📈 3. DCA 백테스팅 시뮬레이터":
    st.header("📈 3. DCA 백테스팅 시뮬레이터")
    st.markdown("초기 자본금과 매일 적립할 금액을 설정하고, 내 포트폴리오의 과거 성과를 분석합니다.")

    with st.form("dca_settings"):
        st.subheader("⚙️ 1. 백테스트 환경 설정")
        col1, col2, col3 = st.columns(3)
        initial_invest = col1.number_input("초기 시작 금액 ($)", min_value=0.0, value=0.0, step=100.0)
        daily_invest = col2.number_input("매일 추가 투자 금액 ($)", min_value=0.0, value=80.0, step=10.0)
        start_date = col3.date_input("백테스트 시작 날짜", value=pd.to_datetime("2024-01-01"))
        
        col4, col5 = st.columns(2)
        cash_interest_rate = col4.number_input("원금 연이율 (Cash Interest Rate, %)", min_value=0.0, value=0.0, step=0.1)
        with col5:
            st.markdown("<br>", unsafe_allow_html=True)
            reinvest_dividends = st.checkbox("🔄 배당 재투자 (Reinvest Dividends)", value=True, help="체크 시 배당금 수익이 차트에 복리로 계산(Adj Close)됩니다.")

        st.markdown("---")
        st.subheader("💼 2. 포트폴리오 자산 배분 (Portfolio Allocation)")
        
        col_port, col_bench = st.columns([2, 1])
        with col_port:
            default_portfolio_data = pd.DataFrame({
                "Ticker": ["QLD", "MAGS", "TQQQ", "BRK-B", "SPY", ""],
                "포트폴리오 1 (%)": [30.0, 20.0, 10.0, 5.0, 0.0, 0.0],
                "포트폴리오 2 (%)": [0.0, 0.0, 0.0, 0.0, 100.0, 0.0]
            })
            edited_df = st.data_editor(
                default_portfolio_data, 
                num_rows="dynamic", 
                use_container_width=True,
                column_config={
                    "Ticker": st.column_config.TextColumn("티커 (예: AAPL)", required=True),
                    "포트폴리오 1 (%)": st.column_config.NumberColumn("포트폴리오 1 (%)", min_value=0, max_value=100, step=1),
                    "포트폴리오 2 (%)": st.column_config.NumberColumn("포트폴리오 2 (%)", min_value=0, max_value=100, step=1)
                }
            )

        with col_bench:
            st.markdown("**비교할 벤치마크 (Benchmarks)**")
            benchmarks = st.multiselect(
                "벤치마크 지수 추가",
                ["SPY", "QQQ", "VOO", "TQQQ", "QLD", "BTC-USD", "SOXX", "GLD"],
                default=["SPY", "QQQ"]
            )
            
        submitted = st.form_submit_button("백테스트 실행 및 분석 🚀", use_container_width=True)

    # 퍼포먼스 요약 계산 함수
    def calc_performance_metrics(equity_series, i_invest, d_invest, c_rate):
        shifted = equity_series.shift(1).fillna(i_invest)
        denominator = shifted + d_invest
        
        rets = np.zeros(len(equity_series))
        mask = denominator != 0
        rets[mask] = (equity_series.values[mask] / denominator.values[mask]) - 1
        rets = pd.Series(rets, index=equity_series.index)
        rets.iloc[0] = 0.0

        total_inv = i_invest + d_invest * len(equity_series)
        end_bal = equity_series.iloc[-1]
        
        roi = (end_bal / total_inv - 1) * 100 if total_inv > 0 else 0
        years = len(equity_series) / 252
        cagr = ((end_bal / total_inv) ** (1 / years) - 1) * 100 if years > 0 and end_bal > 0 and total_inv > 0 else 0

        roll_max = equity_series.cummax()
        dd = (equity_series / roll_max - 1) * 100
        mdd = dd.min() if not dd.empty else 0
        std_dev = rets.std() * np.sqrt(252) * 100

        rf_daily = (1 + c_rate/100)**(1/252) - 1
        excess_rets = rets - rf_daily
        sharpe = (excess_rets.mean() * 252) / (rets.std() * np.sqrt(252)) if rets.std() != 0 else 0

        downside = excess_rets[excess_rets < 0]
        sortino = (excess_rets.mean() * 252) / (downside.std() * np.sqrt(252)) if not downside.empty and downside.std() != 0 else 0

        yearly_rets = (1 + rets).groupby(rets.index.year).prod() - 1
        best_yr = yearly_rets.max() * 100 if not yearly_rets.empty else 0
        worst_yr = yearly_rets.min() * 100 if not yearly_rets.empty else 0

        return [
            f"${i_invest:,.0f}",          
            f"${total_inv:,.0f}",         
            f"${end_bal:,.0f}",           
            f"{roi:.2f}%",                
            f"{cagr:.2f}%",               
            f"{std_dev:.2f}%",            
            f"{best_yr:.2f}%",            
            f"{worst_yr:.2f}%",           
            f"{mdd:.2f}%",                
            f"{sharpe:.2f}",              
            f"{sortino:.2f}"              
        ]

    @st.cache_data(ttl=900)
    def load_backtest_data(tickers, s_date):
        df = yf.download(tickers, start=s_date, auto_adjust=False, progress=False)
        return df

    if submitted:
        port1, port2 = {}, {}
        for _, row in edited_df.iterrows():
            t = str(row["Ticker"]).strip().upper()
            if not t: continue
            if "." in t and t not in ["KRW", "EUR"]: t = t.replace(".", "-")
            
            w1 = pd.to_numeric(row["포트폴리오 1 (%)"], errors='coerce')
            w2 = pd.to_numeric(row["포트폴리오 2 (%)"], errors='coerce')
            
            if pd.notna(w1) and w1 > 0: port1[t] = w1
            if pd.notna(w2) and w2 > 0: port2[t] = w2
            
        tot_w1 = sum(port1.values())
        tot_w2 = sum(port2.values())
        if tot_w1 > 0: port1 = {k: v/tot_w1 for k, v in port1.items()}
        if tot_w2 > 0: port2 = {k: v/tot_w2 for k, v in port2.items()}

        target_tickers = set(benchmarks)
        target_tickers.update(port1.keys())
        target_tickers.update(port2.keys())
        
        if not target_tickers:
            st.error("티커를 하나 이상 입력하거나 벤치마크를 선택해주세요.")
        else:
            with st.spinner("과거 데이터를 기반으로 시뮬레이션 중입니다..."):
                df_raw_bt = load_backtest_data(list(target_tickers), start_date.strftime("%Y-%m-%d"))
                
                price_col = 'Adj Close' if reinvest_dividends else 'Close'
                
                if isinstance(df_raw_bt.columns, pd.MultiIndex):
                    try:
                        df_bt = df_raw_bt[price_col]
                    except KeyError:
                        df_bt = df_raw_bt['Close'] 
                else:
                    df_bt = df_raw_bt[price_col].to_frame(name=list(target_tickers)[0])
                    
                df_bt = df_bt.dropna()
                
                if df_bt.empty:
                    st.error("데이터 기간 교집합이 없습니다. (최근 상장된 종목이나 잘못된 티커가 있는지 확인하세요.)")
                else:
                    results = pd.DataFrame(index=df_bt.index)
                    
                    dr = (1 + cash_interest_rate / 100) ** (1 / 252) - 1
                    cash_bal = initial_invest
                    cash_hist = []
                    for _ in range(len(df_bt)):
                        cash_bal = cash_bal * (1 + dr) + daily_invest
                        cash_hist.append(cash_bal)
                    results["원금+이자 (Cash)"] = cash_hist

                    portfolios_to_run = {"포트폴리오 1": port1, "포트폴리오 2": port2}
                    for p_name, p_weights in portfolios_to_run.items():
                        if not p_weights: continue
                        val_series = pd.Series(0.0, index=df_bt.index)
                        for t, w in p_weights.items():
                            if t in df_bt.columns:
                                i_alloc = initial_invest * w
                                d_alloc = daily_invest * w
                                
                                initial_shares = i_alloc / df_bt[t].iloc[0]
                                daily_shares = d_alloc / df_bt[t]
                                
                                cum_shares = initial_shares + daily_shares.cumsum()
                                val_series += cum_shares * df_bt[t]
                        results[p_name] = val_series
                    
                    for b in benchmarks:
                        if b in df_bt.columns:
                            initial_shares = initial_invest / df_bt[b].iloc[0]
                            daily_shares = daily_invest / df_bt[b]
                            cum_shares = initial_shares + daily_shares.cumsum()
                            results[b] = cum_shares * df_bt[b]

                    st.markdown("---")
                    st.markdown("### 📋 퍼포먼스 요약 (Performance Summary)")
                    
                    metric_names = [
                        "Start Balance (시작 금액)", "Total Invested (총 투자금)", "End Balance (최종 평가금)",
                        "Total Return (총 수익률)", "Annualized Return (CAGR)", "Standard Deviation (변동성)",
                        "Best Year (최고 연도)", "Worst Year (최악 연도)", "Maximum Drawdown (최대 낙폭)",
                        "Sharpe Ratio (샤프 지수)", "Sortino Ratio (소르티노 지수)"
                    ]
                    
                    summary_df = pd.DataFrame(index=metric_names)
                    for col in results.columns:
                        summary_df[col] = calc_performance_metrics(results[col], initial_invest, daily_invest, cash_interest_rate)

                    st.dataframe(summary_df, use_container_width=True)
                    
                    st.markdown("---")
                    st.markdown("### 📈 포트폴리오 성장 곡선 (Portfolio Growth)")
                    st.line_chart(results, height=400)
                    
                    chart_col1, chart_col2 = st.columns(2)
                    with chart_col1:
                        st.markdown("#### 📊 연도별 수익률 (Annual Returns)")
                        
                        eq_only = results.drop(columns=["원금+이자 (Cash)"])
                        annual_rets_dict = {}
                        
                        for col in eq_only.columns:
                            series = eq_only[col]
                            shifted = series.shift(1).fillna(initial_invest)
                            denominator = shifted + daily_invest
                            
                            rets = np.zeros(len(series))
                            mask = denominator != 0
                            rets[mask] = (series.values[mask] / denominator.values[mask]) - 1
                            rets = pd.Series(rets, index=series.index)
                            rets.iloc[0] = 0.0
                            
                            yearly_rets = (1 + rets).groupby(rets.index.year).prod() - 1
                            annual_rets_dict[col] = yearly_rets * 100
                            
                        annual_rets = pd.DataFrame(annual_rets_dict)
                        annual_rets.index = annual_rets.index.astype(str)
                        st.bar_chart(annual_rets, height=350)
                    
                    with chart_col2:
                        st.markdown("#### 📉 낙폭 추이 (Underwater/Drawdowns)")
                        roll_max_eq = eq_only.cummax()
                        dd_curve = (eq_only / roll_max_eq - 1) * 100
                        st.line_chart(dd_curve, height=350)