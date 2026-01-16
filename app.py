import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Gold Spread & Macro", page_icon="💰", layout="centered")

# --- 함수: 데이터 가져오기 (안전한 버전) ---
def get_financial_data():
    # 티커 목록
    tickers = {
        'Gold_Intl_USD': 'GC=F',       # 금 선물
        'Exchange_Rate': 'KRW=X',      # 환율
        'SP500': '^GSPC',              # S&P 500
        'Trans_Avg': '^DJT',           # 운송 지수
        'US_10Y': '^TNX'               # 미국채 10년
    }
    
    result = {}
    
    # 각 데이터를 개별적으로 가져와서 오류 방지
    for key, ticker_symbol in tickers.items():
        try:
            # 최근 5일치 데이터를 가져와서 가장 마지막(최신) 값을 씀
            # (주말이나 시차 때문에 '오늘' 데이터가 없을 수 있으므로)
            df = yf.Ticker(ticker_symbol).history(period="5d")
            if not df.empty:
                last_price = df['Close'].iloc[-1]
                result[key] = last_price
            else:
                result[key] = 0.0
        except Exception:
            result[key] = 0.0
            
    return result

def get_krx_gold_price():
    # 네이버 금융에서 KRX 금값 크롤링
    url = "https://finance.naver.com/marketindex/goldDetail.naver"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        price_str = soup.select_one("em.no_up")
        if not price_str:
            price_str = soup.select_one("em.no_down")
        if not price_str:
             # 변동이 없을 때(보합)는 no_up/down 클래스가 없을 수 있음
             price_str = soup.select_one("em.no_today")
             
        if price_str:
            return float(price_str.get_text(strip=True).replace(',', ''))
        return 0.0
    except:
        return 0.0

# --- 메인 로직 ---
st.title("💰 Gold & Market Watch")
st.caption(f"Update: {time.strftime('%Y-%m-%d %H:%M:%S')} KST")

if st.button('데이터 새로고침 🔄'):
    st.rerun()

with st.spinner('미국 및 한국 시장 데이터를 조회 중...'):
    macro_data = get_financial_data()
    krx_gold = get_krx_gold_price()
    
    # 변수 할당
    intl_gold_usd = macro_data.get('Gold_Intl_USD', 0)
    exchange_rate = macro_data.get('Exchange_Rate', 1300) # 기본값 안전장치
    
    # 0원이나 에러가 떴을 때를 대비한 안전장치
    if intl_gold_usd == 0 or exchange_rate == 0:
        st.error("미국 시장 데이터를 불러오는데 실패했습니다. 잠시 후 다시 시도해주세요.")
        intl_gold_krw_g = 0
        spread = 0
    else:
        # 1 트로이온스 = 31.1034768 g
        intl_gold_krw_g = (intl_gold_usd * exchange_rate) / 31.1034768
        
        if krx_gold > 0:
            spread = ((krx_gold - intl_gold_krw_g) / intl_gold_krw_g) * 100
        else:
            spread = 0

    # --- 화면 표시 ---
    st.divider()
    st.subheader("📊 금 가격 괴리율 (Kim-P)")
    
    c1, c2 = st.columns(2)
    c1.metric("KRX 금시세 (g)", f"{krx_gold:,.0f}원")
    
    if intl_gold_krw_g > 0:
        c2.metric("국제 이론가 (g)", f"{intl_gold_krw_g:,.0f}원", help="국제 금값(달러) × 환율 ÷ 31.1035")
        
        st.metric(
            "괴리율 (Spread)", 
            f"{spread:.2f}%", 
            delta=f"{spread:.2f}%",
            delta_color="inverse"
        )
        if spread > 1.0:
            st.warning(f"⚠️ 국내 금값이 국제 시세보다 {spread:.1f}% 더 비쌉니다.")
        elif spread < -0.5:
            st.success("✅ 국내 금값이 더 저렴합니다 (역프리미엄).")
        else:
            st.info("ℹ️ 가격 차이가 적정 수준입니다.")
    else:
        st.warning("국제 금 시세 데이터를 가져오지 못했습니다.")

    st.divider()
    st.subheader("🌍 주요 시장 지표")
    
    t1, t2 = st.tabs(["🇺🇸 미국 지표", "🚛 경기/운송"])
    
    with t1:
        col1, col2, col3 = st.columns(3)
        col1.metric("환율 (USD/KRW)", f"{exchange_rate:,.1f}원")
        col2.metric("S&P 500", f"{macro_data.get('SP500', 0):,.0f}")
        col3.metric("미국채 10년", f"{macro_data.get('US_10Y', 0):.2f}%")
        
    with t2:
        st.metric("다우 운송지수", f"{macro_data.get('Trans_Avg', 0):,.0f}")
        st.caption("*운송지수는 실물 경기 선행 지표로 활용됩니다.")
