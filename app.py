import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import plotly.express as px  # 공정표(Gantt) 차트를 위해 추가

# 1. 페이지 설정
st.set_page_config(
    page_title="나만의 통합 대시보드", 
    page_icon="💰", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. CSS 스타일 (모바일 최적화)
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    button[data-baseweb="tab"] { font-size: 1.1rem !important; font-weight: 600 !important; }
    .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- [함수 1] 금융 데이터 가져오기 ---
@st.cache_data(ttl=300)
def get_financial_data():
    tickers = {
        'Gold_Intl_USD': 'GC=F', 'Exchange_Rate': 'KRW=X',
        'SP500': '^GSPC', 'Nasdaq': '^IXIC',
        'Trans_Avg': '^DJT', 'US_10Y': '^TNX'
    }
    result = {}
    for key, ticker_symbol in tickers.items():
        try:
            df = yf.Ticker(ticker_symbol).history(period="5d")
            result[key] = df['Close'].iloc[-1] if not df.empty else 0.0
        except:
            result[key] = 0.0
    return result

# --- [함수 2] 국내 금 시세 크롤링 ---
def get_krx_gold_price():
    url = "https://finance.naver.com/marketindex/goldDetail.naver"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        price_str = soup.select_one("em.no_up") or soup.select_one("em.no_down") or soup.select_one("em.no_today")
        if price_str:
            return float(price_str.get_text(strip=True).replace(',', ''))
        return 0.0
    except:
        return 0.0

# --- [함수 3] 공정표 샘플 데이터 생성 (엑셀 없을 때용) ---
def get_sample_schedule():
    data = [
        dict(Task="기초 공사", Start='2024-01-01', Finish='2024-02-28', Department="토목팀", Completion=100),
        dict(Task="골조 공사", Start='2024-03-01', Finish='2024-05-15', Department="건축팀", Completion=60),
        dict(Task="전기 배선", Start='2024-04-15', Finish='2024-06-30', Department="전기팀", Completion=30),
        dict(Task="내부 인테리어", Start='2024-06-01', Finish='2024-08-30', Department="인테리어팀", Completion=0),
        dict(Task="준공 검사", Start='2024-09-01', Finish='2024-09-15', Department="QM팀", Completion=0)
    ]
    return pd.DataFrame(data)

# --- 메인 화면 구성 ---
st.title("💰 Chan's 통합 대시보드 (Finance & PM)")
st.caption(f"Last Update: {time.strftime('%m-%d %H:%M')}")

if st.button('데이터 전체 새로고침 🔄', use_container_width=True):
    st.rerun()

# 탭 구성 (여기에 공정표 탭을 추가했습니다)
tab1, tab2, tab3 = st.tabs(["📊 금/시장 지표", "🚛 경기/물동량", "🏗️ 공정표 관리"])

# --- [탭 1] 금 시세 및 주요 지표 ---
with tab1:
    with st.spinner('시장 데이터 수신 중...'):
        macro_data = get_financial_data()
        krx_gold = get_krx_gold_price()
        
        intl_gold_usd = macro_data.get('Gold_Intl_USD', 0)
        exchange_rate = macro_data.get('Exchange_Rate', 1300)
        
        intl_gold_krw_g = (intl_gold_usd * exchange_rate) / 31.1034768 if intl_gold_usd > 0 else 0
        spread = ((krx_gold - intl_gold_krw_g) / intl_gold_krw_g) * 100 if intl_gold_krw_g > 0 else 0

        # 금 시세 섹션
        st.subheader("Gold Spread Check")
        with st.container(border=True):
            col1, col2, col3 = st.columns([1, 1, 1.2]) 
            col1.metric("KRX 국내시세 (g)", f"{krx_gold:,.0f}원")
            col2.metric("국제 이론가 (g)", f"{intl_gold_krw_g:,.0f}원")
            col3.metric("괴리율 (Spread)", f"{spread:.2f}%", delta=f"{spread:.2f}%", delta_color="inverse")
            
            if spread > 1.0: st.warning(f"⚠️ 국내가 {spread:.1f}% 더 비쌉니다.")
            elif spread < -0.5: st.success("✅ 국내가 더 저렴합니다 (역프리미엄).")

        st.divider()
        
        # 주요 지표 섹션
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("환율 (USD)", f"{exchange_rate:,.1f}원")
        c2.metric("S&P 500", f"{macro_data.get('SP500', 0):,.0f}")
        c3.metric("나스닥", f"{macro_data.get('Nasdaq', 0):,.0f}")
        c4.metric("미국채 10년", f"{macro_data.get('US_10Y', 0):.2f}%")

# --- [탭 2] 경기/물동량 ---
with tab2:
    st.subheader("Global Logistics & Trend")
    c_a, c_b = st.columns(2)
    with c_a:
         st.metric("다우 운송지수", f"{macro_data.get('Trans_Avg', 0):,.0f}")
    with c_b:
         st.caption("운송지수는 실물 경기의 선행 지표입니다. (Dow Jones Trans.)")
    
    try:
        chart_data = yf.Ticker('^DJT').history(period='1mo')['Close']
        st.line_chart(chart_data)
    except:
        st.write("차트 로딩 실패")

# --- [탭 3] 공정표 (새로 추가된 부분) ---
with tab3:
    st.subheader("🏗️ 프로젝트 공정 관리 (Gantt Chart)")
    
    # 파일 업로더
    uploaded_file = st.file_uploader("엑셀 공정표 업로드 (없으면 샘플 표시)", type=['xlsx', 'xls'])
    
    if uploaded_file:
        try:
            df_schedule = pd.read_excel(uploaded_file)
            st.success(f"📂 {uploaded_file.name} 로드 완료!")
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")
            df_schedule = get_sample_schedule()
    else:
        st.info("💡 파일을 업로드하면 내 공정표를 볼 수 있습니다. (현재는 샘플 데이터)")
        df_schedule = get_sample_schedule()

    # 데이터 전처리 (날짜 형식 변환 등)
    if not df_schedule.empty:
        # 차트 그리기
        fig = px.timeline(
            df_schedule, 
            x_start="Start", 
            x_end="Finish", 
            y="Task", 
            color="Completion", # 진행률에 따라 색상 변경
            color_continuous_scale="Blues", # 파란색 계열
            hover_data=["Department", "Completion"],
            title="Project Schedule Timeline"
        )
        
        # 차트 디자인 다듬기
        fig.update_yaxes(autorange="reversed") # 위에서부터 순서대로
        fig.layout.xaxis.type = 'date'
        fig.update_layout(height=500) # 높이 설정

        st.plotly_chart(fig, use_container_width=True)
        
        # 데이터 테이블도 같이 보여주기
        with st.expander("📋 데이터 원본 보기"):
            st.dataframe(df_schedule, use_container_width=True)
