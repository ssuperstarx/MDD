import tkinter as tk
from tkinter import ttk, messagebox
import yfinance as yf
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class MDDDashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MDD 통합 대시보드 (ETF 모니터링)")
        self.root.geometry("1050x800")
        self.root.resizable(True, True)
        
        # 주시할 대상 ETF 7종목
        self.tickers = ["QQQ", "SPY", "IWM", "HYG", "LQD", "XLY", "XLP"]
        
        # 각 티커별 테마/관련주 정보 매핑
        self.ticker_themes = {
            "QQQ": "나스닥 100 (미국 기술주)",
            "SPY": "S&P 500 (미국 대형주 전체)",
            "IWM": "러셀 2000 (미국 중소형주)",
            "HYG": "하이일드 회사채 (고위험/고수익)",
            "LQD": "투자등급 회사채 (우량 회사채)",
            "XLY": "경기소비재 (아마존, 테슬라 등)",
            "XLP": "필수소비재 (P&G, 코카콜라 등)"
        }
        
        self.data = {}
        self.analysis_results = {}
        
        self.create_header()
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.root.after(100, self.load_and_analyze)

    def create_header(self):
        header_frame = ttk.Frame(self.root, padding=10)
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(header_frame, text="📊 미국 주요 ETF 하락장 모니터링", font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(header_frame, text="데이터를 불러오는 중입니다. 잠시만 기다려주세요...", font=("Arial", 11), foreground="blue")
        self.status_label.pack(side=tk.RIGHT)

    def load_and_analyze(self):
        end_date = datetime.today()
        start_date = end_date - relativedelta(years=20)
        
        try:
            df = yf.download(self.tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
            
            if df.empty:
                raise ValueError("데이터를 가져오지 못했습니다.")
                
            if isinstance(df.columns, pd.MultiIndex):
                close_prices = df['Close']
            else:
                close_prices = df['Close']
            
            for ticker in self.tickers:
                prices = close_prices[ticker].dropna()
                self.analyze_ticker(ticker, prices)
                
            self.status_label.config(text=f"업데이트 완료: {end_date.strftime('%Y-%m-%d')}", foreground="green")
            self.build_ui()
            
        except Exception as e:
            messagebox.showerror("오류", f"데이터 로드 중 문제가 발생했습니다:\n{e}")
            self.status_label.config(text="업데이트 실패", foreground="red")

    def analyze_ticker(self, ticker, prices):
        # 1. 고점 및 하락률 계산
        roll_max_20y = prices.cummax()
        drawdown_20y = (prices / roll_max_20y - 1.0) * 100
        mdd_20y = drawdown_20y.min()
        current_dd_20y = drawdown_20y.iloc[-1]
        
        # 2. 현재 하락 지속 기간 계산 (마지막 고점 기준)
        is_peak = prices == roll_max_20y
        peak_dates = prices[is_peak].index
        
        last_peak = peak_dates[-1] if len(peak_dates) > 0 else prices.index[0]
        ongoing_days = (prices.index[-1] - last_peak).days
        
        # 3. 주요 회복 구간 리스트 계산 (50일 이상)
        recovery_list = []
        for i in range(len(peak_dates) - 1):
            start = peak_dates[i]
            end = peak_dates[i+1]
            days = (end - start).days
            if days >= 50:
                period_mdd = drawdown_20y.loc[start:end].min()
                recovery_list.append((start, end, days, period_mdd))
                
        if ongoing_days >= 50:
            period_mdd = drawdown_20y.loc[last_peak:].min()
            recovery_list.append((last_peak, None, ongoing_days, period_mdd))
            
        recovery_list.sort(key=lambda x: x[2], reverse=True)
        
        # 4. 구간 판단 로직
        if current_dd_20y <= -20.0:
            status = "🔴 물타기 구간"
            status_desc = "고점 대비 20% 이상 하락 (바겐세일 적극 검토)"
            color = "#ffcccc"
        elif current_dd_20y <= -10.0:
            status = "🟡 조정 구간"
            status_desc = "고점 대비 10~20% 하락 (분할 매수 준비)"
            color = "#fff0b3"
        else:
            status = "🔵 안정 구간"
            status_desc = "고점 대비 10% 이내 하락 (월 적립 매수 유지)"
            color = "#cce6ff"
            
        self.analysis_results[ticker] = {
            'drawdown_20y': drawdown_20y,
            'mdd_20y': mdd_20y,
            'current_dd_20y': current_dd_20y,
            'recovery_list': recovery_list,
            'status': status,
            'status_desc': status_desc,
            'bg_color': color,
            'last_peak': last_peak,
            'ongoing_days': ongoing_days
        }

    def build_ui(self):
        # 1. 종합 대시보드 탭
        dash_tab = ttk.Frame(self.notebook)
        self.notebook.add(dash_tab, text=" 📊 종합 대시보드 ")
        self.build_dashboard_tab(dash_tab)
        
        # 2. 개별 종목 탭
        for ticker in self.tickers:
            tab_frame = ttk.Frame(self.notebook)
            self.notebook.add(tab_frame, text=f" {ticker} ")
            self.build_ticker_tab(tab_frame, ticker)

    def build_dashboard_tab(self, parent):
        canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        columns = 3
        for i in range(columns):
            scrollable_frame.columnconfigure(i, weight=1, minsize=300)

        for i, ticker in enumerate(self.tickers):
            row = i // columns
            col = i % columns
            res = self.analysis_results[ticker]
            theme_text = self.ticker_themes.get(ticker, "기타/알 수 없음")
            
            card = tk.Frame(scrollable_frame, bg=res['bg_color'], bd=2, relief=tk.RIDGE, padx=15, pady=20)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            # 티커와 테마 표시
            tk.Label(card, text=ticker, font=("Arial", 22, "bold"), bg=res['bg_color']).pack(pady=(5, 2))
            tk.Label(card, text=theme_text, font=("Arial", 11), fg="#555555", bg=res['bg_color']).pack(pady=(0, 10))
            
            # 상태 표시
            tk.Label(card, text=res['status'], font=("Arial", 16, "bold"), bg=res['bg_color']).pack(pady=5)
            
            # 현재 하락률 및 유지 기간 로직
            if res['current_dd_20y'] == 0:
                duration_text = "✨ 전고점 갱신 중! (0일)"
            else:
                last_peak_str = res['last_peak'].strftime('%y.%m.%d')
                duration_text = f"하락 지속: {res['ongoing_days']}일째\n(마지막 고점: {last_peak_str})"
            
            info_text = (
                f"현재 하락률: {res['current_dd_20y']:.2f}%\n"
                f"{duration_text}\n\n"
                f"역대 최대 낙폭: {res['mdd_20y']:.2f}%"
            )
            tk.Label(card, text=info_text, font=("Arial", 12), bg=res['bg_color'], justify="center").pack(pady=10)
            tk.Label(card, text=res['status_desc'], font=("Arial", 10), bg=res['bg_color'], fg="#333333").pack(side=tk.BOTTOM, pady=5)

    def build_ticker_tab(self, parent, ticker):
        res = self.analysis_results[ticker]
        
        table_frame = ttk.LabelFrame(parent, text=f"{ticker} 주요 하락 및 회복 구간 (50일 이상)")
        table_frame.pack(fill=tk.X, padx=10, pady=5)
        
        cols = ("rank", "start", "end", "days", "mdd")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=4)
        tree.heading("rank", text="순위")
        tree.heading("start", text="하락 시작일(고점)")
        tree.heading("end", text="전고점 회복일")
        tree.heading("days", text="소요 일수")
        tree.heading("mdd", text="해당 구간 낙폭")
        
        for col in cols:
            tree.column(col, anchor="center", width=120)
        tree.column("rank", width=60)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        for idx, r in enumerate(res['recovery_list'], 1):
            start_str = r[0].strftime('%Y-%m-%d')
            end_str = r[1].strftime('%Y-%m-%d') if r[1] else "현재 진행중"
            tree.insert("", tk.END, values=(f"{idx}위", start_str, end_str, f"{r[2]}일", f"{r[3]:.2f}%"))
            
        chart_frame = tk.Frame(parent, bg="white", bd=2, relief=tk.SUNKEN)
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        dd = res['drawdown_20y']
        
        ax.plot(dd.index, dd, color='red', alpha=0.8)
        ax.fill_between(dd.index, dd, 0, color='red', alpha=0.2)
        
        for r in res['recovery_list']:
            end_date = r[1] if r[1] else dd.index[-1]
            ax.axvspan(r[0], end_date, color='gold', alpha=0.3)
            mdd_date = dd.loc[r[0]:end_date].idxmin()
            ax.plot(mdd_date, r[3], marker='v', color='darkred', markersize=5)
            
        ax.set_title(f"{ticker} 20-Year Drawdown Map", fontsize=11)
        ax.axhline(0, color='black', linewidth=1)
        ax.axhline(res['mdd_20y'], color='grey', linestyle='--', linewidth=1)
        ax.axhline(-20, color='blue', linestyle=':', linewidth=1.5, label='-20% Threshold')
        ax.grid(True, linestyle='--', alpha=0.5)
        
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = MDDDashboardApp(root)
    root.mainloop()