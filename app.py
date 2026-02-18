import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ============================================================
# 1. 페이지 및 기본 설정
# ============================================================
st.set_page_config(page_title="종합 투자 대시보드", page_icon="📊", layout="wide")
st.title("📊 통합 투자 대시보드")
st.markdown("MDD 기반의 하락장 모니터링과 RAI 지표 기반의 자동 리밸런싱 시그널을 확인하세요.")

tickers_mdd = ["QQQ", "SPY", "IWM", "HYG", "LQD", "XLY", "XLP", "MAGS", "QLD"]
tickers_rebal = ["SPY", "QQQ", "IWM", "HYG", "LQD", "XLY", "XLP", "^VIX", "^VIX3M", "SHY"]
all_tickers = list(set(tickers_mdd + tickers_rebal))

ticker_themes = {
    "QQQ": "나스닥 100", "SPY": "S&P 500", "IWM": "러셀 2000",
    "HYG": "하이일드 채권", "LQD": "투자등급 채권", "XLY": "경기소비재", "XLP": "필수소비재",
    "MAGS": "매그니피센트 7", "QLD": "나스닥 100 (2배)"
}

# ============================================================
# 2. 전역 데이터 로드
# ============================================================
@st.cache_data(ttl=3600)
def load_data():
    end_date = datetime.today()
    start_date = end_date - relativedelta(years=20)
    df = yf.download(all_tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
    return df

with st.spinner('실시간 주가 데이터를 불러오는 중입니다...'):
    df_raw = load_data()

if isinstance(df_raw.columns, pd.MultiIndex):
    close_prices = df_raw['Close']
    high_prices = df_raw['High']
    low_prices = df_raw['Low']
else:
    close_prices = df_raw

# ============================================================
# 3. 화면 분할 (Tabs)
# ============================================================
# ------------------------------------------------------------
# 3. 화면 분할 (Sidebar Navigation)
# ------------------------------------------------------------
st.sidebar.header("메뉴 선택")
page = st.sidebar.radio(
    "페이지 선택", 
    ["📊 1. ETF 하락장 모니터링 (MDD)", "🔄 2. 포트폴리오 리밸런싱 시그널 (RAI)"],
    index=0,
    label_visibility="collapsed",
    key="main_navigation"
)

# ------------------------------------------------------------
# [PAGE 1] 기존 ETF 대시보드
# ------------------------------------------------------------
if page == "📊 1. ETF 하락장 모니터링 (MDD)":
    cols = st.columns(3)
    for i, ticker in enumerate(tickers_mdd):
        if ticker not in close_prices.columns: continue
        prices = close_prices[ticker].dropna()
        if prices.empty: continue
        
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

        with cols[i % 3]:
            st.subheader(f"{ticker} - {ticker_themes.get(ticker, '')}")
            st.markdown(f"**상태:** :{color}[{status}]")
            
            if current_dd_20y == 0:
                st.metric(label="현재 하락률", value="✨ 전고점 갱신 중!")
            else:
                st.metric(label=f"현재 하락률 (마지막 고점: {last_peak.strftime('%y.%m.%d')} / {ongoing_days}일째)", 
                          value=f"{current_dd_20y:.2f}%")
            st.caption(f"역대 최대 낙폭(MDD): {mdd_20y:.2f}%")
            
            fig, ax = plt.subplots(figsize=(5, 2.5))
            ax.plot(drawdown_20y.index, drawdown_20y, color='red', alpha=0.8, linewidth=1)
            ax.fill_between(drawdown_20y.index, drawdown_20y, 0, color='red', alpha=0.2)
            ax.axhline(0, color='black', linewidth=0.8)
            ax.axhline(-20, color='blue', linestyle=':', linewidth=1.5)
            ax.set_ylabel("Drawdown (%)", fontsize=8)
            ax.tick_params(axis='both', which='major', labelsize=8)
            ax.grid(True, linestyle='--', alpha=0.3)
            st.pyplot(fig)
            st.markdown("---")

# ------------------------------------------------------------
# [PAGE 2] RAI 기반 동적 리밸런싱
# ------------------------------------------------------------
elif page == "🔄 2. 포트폴리오 리밸런싱 시그널 (RAI)":
    st.markdown("### ⚙️ 리밸런싱 파라미터 및 성향 설정")
    
    # UI에서 변수 및 투자 성향 입력받기 (4등분)
    col1, col2, col3, col4 = st.columns(4)
    port_val = col1.number_input("현재 포트폴리오 금액 ($)", min_value=100, value=10000, step=100)
    cur_q_weight = col2.number_input("현재 QQQ 비중 (0.0~1.0)", min_value=0.0, max_value=1.0, value=0.70, step=0.05)
    rebal_freq = col3.selectbox("리밸런싱 기준일", ["D (매일)", "W-FRI (주 1회 금요일)", "M (월말)"])
    rebal_freq_val = rebal_freq.split(" ")[0]
    
    # 투자 성향 옵션 추가
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

    # ★ 개선점: 성향에 따른 동적 비중(Target Weight) 매핑 로직
    def quantile_to_weight(q: float, strat: str) -> float:
        if "방어형" in strat:
            # 방어형: 점수가 낮을 때 주식 비중을 극단적으로 줄임 (현금 확보 우선)
            if q <= 0.10: return 0.20
            elif q <= 0.25: return 0.40
            elif q <= 0.50: return 0.60
            elif q <= 0.75: return 0.80
            else: return 1.00
        elif "공격형" in strat:
            # 공격형: 최악의 하락장에서도 주식 비중을 60% 이상 유지 (수익 추구)
            if q <= 0.10: return 0.60
            elif q <= 0.25: return 0.70
            elif q <= 0.50: return 0.80
            elif q <= 0.75: return 0.90
            else: return 1.00
        else: 
            # 중립형: 제공해주신 기본 로직
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
    
    # 여기서 선택한 성향(strategy)을 함수에 전달합니다.
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

    # ★ 추가된 원리 설명 구간
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
    