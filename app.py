import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import plotly.express as px

# 1. 페이지 설정 (반드시 코드 최상단에 위치)
st.set_page_config(
    page_title="통합 대시보드",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. CSS 스타일 설정
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    button[data-baseweb="tab"] { font-size: 1.1rem !important; font-weight: 600 !important; }
    .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 함수: 금융 데이터 가져오기 ---
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
            # yfinance 데이터 가져오기
            df = yf.Ticker(ticker_symbol).history(period="5d")
            if not df.empty:
                result[key] = df['Close'].iloc[-1]
            else:
                result[key] = 0.0
        except Exception as e:
            # 에러 발생 시 로그를 남기지 않고 0으로 처리 (화면 깨짐 방지)
            result[key] = 0.0
    return result

# --- 함수: 국내 금 시세 크롤링 (헤더 추가로 차단 방지) ---
def get_krx_gold_price():
    url = "https://finance.naver.com/marketindex/goldDetail.naver"
    # 봇 차단 방지를 위한 헤더 추가
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 네이버 금융 구조에 따른 가격 찾기
        price_str = soup.select_one("em.no_up")
        if not price_str: price_str = soup.select_one("em.no_down")
        if not price_str: price_str = soup.select_one("em.no_today")
        
        if price_str:
            return float(price_str.get_text(strip=True).replace(',', ''))
        return 0.0
    except Exception as e:
        return 0.0

# --- 함수: 공정표 샘플 데이터 ---
def get_sample_schedule():
    data = [
        dict(Task="기초 공사", Start='2024-01-01', Finish='2024-02-28', Department="토목팀", Completion=100),
        dict(Task="골조 공사", Start='2024-03-01', Finish='2024-05-15', Department="건축팀", Completion=60),
        dict(Task="전기 배선", Start='2024-04-15', Finish='2024-06-30', Department="전기팀", Completion=30),
        dict(Task="내부 인테리어", Start='2024-06-01', Finish='2024-08-30', Department="인테리어팀", Completion=0),
        dict(Task="준공 검사", Start='2024-09-01', Finish='2024-09-15', Department="QM팀", Completion=0)
    ]
    return pd.DataFrame(data)

# --- 메인 화면 시작 ---
st.title("💰 Chan's 통합 대시보드")
st.caption(f"Last Update: {time.strftime('%Y-%m-%d %H:%M')}")

if st.button('데이터 새로고침 🔄', use_container_width=True):
    st.rerun()

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📊 금/시장 지표", "🚛 경기/물동량", "🏗️ 공정표 관리"])

# --- [탭 1] 금/시장 지표 ---
with tab1:
    with st.spinner('데이터를 불러오는 중...'):
        macro_data = get_financial_data()
        krx_gold = get_krx_gold_price()
        
        # 계산 로직
        intl_gold_usd = macro_data.get('Gold_Intl_USD', 0)
        exchange_rate = macro_data.get('Exchange_Rate', 1300)
        
        if intl_gold_usd > 0 and exchange_rate > 0:
            intl_gold_krw_g = (intl_gold_usd * exchange_rate) / 31.1034768
            spread = ((krx_gold - intl_gold_krw_g) / intl_gold_krw_g) * 100 if krx_gold > 0 else 0
        else:
            intl_gold_krw_g = 0
            spread = 0

        # 금 시세 표시
        st.subheader("Gold Price Check")
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 1, 1.2])
            c1.metric("KRX 국내시세 (g)", f"{krx_gold:,.0f}원")
            c2.metric("국제 이론가 (g)", f"{intl_gold_krw_g:,.0f}원")
            c3.metric("괴리율 (Spread)", f"{spread:.2f}%", delta=f"{spread:.2f}%", delta_color="inverse")
            
            if spread > 1.0: st.warning(f"국내가 {spread:.1f}% 더 비쌉니다.")
            elif spread < -0.5: st.success("국내가 더 저렴합니다 (역프리미엄).")

        st.divider()
        
        # 시장 지표 표시
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("환율 (USD)", f"{exchange_rate:,.1f}원")
        m2.metric("S&P 500", f"{macro_data.get('SP500', 0):,.0f}")
        m3.metric("나스닥", f"{macro_data.get('Nasdaq', 0):,.0f}")
        m4.metric("미국채 10년", f"{macro_data.get('US_10Y', 0):.2f}%")

# --- [탭 2] 경기 지표 ---
with tab2:
    st.subheader("Transport Index (경기 선행)")
    col_a, col_b = st.columns(2)
    col_a.metric("다우 운송지수", f"{macro_data.get('Trans_Avg', 0):,.0f}")
    col_b.caption("운송지수는 실물 경기의 선행 지표입니다.")
    
    try:
        # 차트 데이터가 있으면 그리기
        chart_data = yf.Ticker('^DJT').history(period='1mo')['Close']
        if not chart_data.empty:
            st.line_chart(chart_data)
        else:
            st.info("차트 데이터를 불러올 수 없습니다.")
    except:
        st.info("차트 데이터를 불러올 수 없습니다.")

# --- [탭 3] 공정표 관리 ---
with tab3:
    st.subheader("🏗️ 프로젝트 공정 관리 (Gantt Chart)")
    
    uploaded_file = st.file_uploader("공정표 엑셀 업로드 (없으면 샘플)", type=['xlsx', 'xls'])
    
    if uploaded_file:
        try:
            df_schedule = pd.read_excel(uploaded_file)
            st.success(f"📂 {uploaded_file.name} 로드 성공")
        except Exception as e:
            st.error(f"파일을 읽는 중 에러가 발생했습니다: {e}")
            df_schedule = get_sample_schedule()
    else:
        df_schedule = get_sample_schedule()

    # 데이터가 있다면 차트 그리기
    if not df_schedule.empty:
        try:
            # 날짜 컬럼 강제 변환 (에러 방지 핵심)
            if 'Start' in df_schedule.columns and 'Finish' in df_schedule.columns:
                df_schedule['Start'] = pd.to_datetime(df_schedule['Start'])
                df_schedule['Finish'] = pd.to_datetime(df_schedule['Finish'])
                
                fig = px.timeline(
                    df_schedule, 
                    x_start="Start", 
                    x_end="Finish", 
                    y="Task", 
                    color="Completion",
                    color_continuous_scale="Blues",
                    title="Project Schedule"
                )
                fig.update_yaxes(autorange="reversed")
                fig.layout.xaxis.type = 'date'
                fig.update_layout(height=400)
                
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("데이터 상세 보기"):
                    st.dataframe(df_schedule, use_container_width=True)
            else:
                st.error("엑셀 파일에 'Start', 'Finish', 'Task' 컬럼이 포함되어야 합니다.")
        except Exception as e:
            st.error(f"차트 생성 중 에러 발생: {e}")
