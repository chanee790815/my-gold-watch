import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# 1. 페이지 설정
st.set_page_config(
    page_title="통합 PMS & 금융 대시보드",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. 스타일 설정
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    button[data-baseweb="tab"] { font-size: 1.1rem !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- [함수 1] 금융 데이터 ---
@st.cache_data(ttl=300)
def get_financial_data():
    tickers = {'Gold_Intl': 'GC=F', 'Ex_Rate': 'KRW=X', 'SP500': '^GSPC', 'Trans': '^DJT'}
    result = {}
    for key, val in tickers.items():
        try:
            df = yf.Ticker(val).history(period="5d")
            result[key] = df['Close'].iloc[-1] if not df.empty else 0.0
        except: result[key] = 0.0
    return result

# --- [함수 2] 금 시세 크롤링 ---
def get_krx_gold():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "https://finance.naver.com/marketindex/goldDetail.naver"
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        price = soup.select_one("em.no_up") or soup.select_one("em.no_down") or soup.select_one("em.no_today")
        return float(price.get_text(strip=True).replace(',', '')) if price else 0.0
    except: return 0.0

# --- [함수 3] 구글 시트 데이터 가져오기 (JWT 에러 해결 로직 포함) ---
def load_data_from_gsheets():
    try:
        # 1. Secrets에서 인증 정보 가져오기
        if "gcp_service_account" not in st.secrets:
            st.error("Secrets에 'gcp_service_account' 정보가 없습니다.")
            return pd.DataFrame()

        # 딕셔너리로 변환
        secrets_dict = dict(st.secrets["gcp_service_account"])

        # ✅ [핵심 수정] 줄바꿈 문자(\n)가 깨진 것을 강제로 고침
        if "private_key" in secrets_dict:
            secrets_dict["private_key"] = secrets_dict["private_key"].replace("\\n", "\n")

        # 2. 인증 및 연결
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(secrets_dict, scopes=scopes)
        client = gspread.authorize(creds)

        # 3. 시트 열기 (Secrets에 저장된 시트 URL 사용)
        sheet_url = st.secrets["private_gsheets_url"]
        sh = client.open_by_url(sheet_url)
        worksheet = sh.get_worksheet(0) # 첫 번째 시트

        # 4. 데이터프레임 변환
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df

    except Exception as e:
        st.error(f"구글 시트 연결 실패: {e}")
        return pd.DataFrame()

# --- [함수 4] 샘플 데이터 (연결 실패 시 대타) ---
def get_sample_schedule():
    return pd.DataFrame([
        dict(Task="샘플: 기초공사", Start='2024-01-01', Finish='2024-02-28', Department="토목팀", Completion=100),
        dict(Task="샘플: 골조공사", Start='2024-03-01', Finish='2024-05-15', Department="건축팀", Completion=60)
    ])

# --- 메인 화면 ---
st.title("🏗️ 당진 적서리 태양광 PMS & Market Watch")
st.caption(f"Last Update: {time.strftime('%Y-%m-%d %H:%M')}")

if st.button('새로고침 🔄', use_container_width=True):
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📊 금/시장 지표", "🚛 경기 동향", "📅 공정 관리(DB)"])

# --- 탭 1 & 2: 금융 정보 (기존 유지) ---
with tab1:
    fin_data = get_financial_data()
    kr_gold = get_krx_gold()
    intl_gold = fin_data.get('Gold_Intl', 0)
    rate = fin_data.get('Ex_Rate', 1300)
    th_price = (intl_gold * rate) / 31.1035 if intl_gold > 0 else 0
    spread = ((kr_gold - th_price)/th_price)*100 if th_price > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("국내 금값", f"{kr_gold:,.0f}원")
    col2.metric("국제 이론가", f"{th_price:,.0f}원")
    col3.metric("괴리율", f"{spread:.2f}%", delta_color="inverse")

with tab2:
    st.metric("다우 운송지수", f"{fin_data.get('Trans', 0):,.0f}")
    try:
        st.line_chart(yf.Ticker('^DJT').history(period='1mo')['Close'])
    except: st.write("차트 로딩 실패")

# --- 탭 3: 구글 시트 공정표 (오류 수정 적용됨) ---
with tab3:
    st.subheader("실시간 공정 현황 (Google Sheets)")
    
    # DB 연결 시도
    with st.spinner("구글 시트 데이터 불러오는 중..."):
        df_schedule = load_data_from_gsheets()
    
    # 실패하면 샘플 데이터 사용
    if df_schedule.empty:
        st.warning("⚠️ 구글 시트 연결에 실패하여 샘플 데이터를 보여줍니다. (Secrets 설정을 확인하세요)")
        df_schedule = get_sample_schedule()
    else:
        st.success("✅ 구글 DB 연결 성공!")

    # 데이터 전처리 및 차트
    try:
        if 'Start' in df_schedule.columns and 'Finish' in df_schedule.columns:
            df_schedule['Start'] = pd.to_datetime(df_schedule['Start'])
            df_schedule['Finish'] = pd.to_datetime(df_schedule['Finish'])
            
            # 검색 기능
            query = st.text_input("검색 (공정명/부서)", placeholder="예: 전기")
            if query:
                mask = df_schedule.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)
                df_view = df_schedule[mask]
            else:
                df_view = df_schedule
            
            # 간트 차트
            fig = px.timeline(df_view, x_start="Start", x_end="Finish", y="Task", 
                              color="Completion", title="Project Schedule", height=400)
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("원본 데이터 확인"):
                st.dataframe(df_view)
        else:
            st.error("데이터에 'Start', 'Finish', 'Task' 컬럼이 꼭 있어야 합니다.")
            st.dataframe(df_schedule)
            
    except Exception as e:
        st.error(f"차트 그리기 오류: {e}")
