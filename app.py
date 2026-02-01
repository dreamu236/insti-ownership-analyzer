import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from io import StringIO
from datetime import datetime

# 1. 페이지 설정 (Modern & Simple 디자인)
st.set_page_config(page_title="Insti-Ownership Analyzer", layout="wide")
st.title("📊 기관 투자자 지분 분석 시스템 (v2.0)")
st.markdown("---")

# 2. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")
    api_key = st.text_input("Google Gemini API 키", type="password", help="AI Studio에서 발급받은 키를 입력하세요.")
    ticker = st.text_input("분석 티커 입력", "RXRX").upper()
    st.info("💡 Tip: 모델은 API 키 입력 시 자동으로 최신 버전을 탐색합니다.")

# 3. 모델 자동 매칭 시스템 (404 오류 방지 핵심)
model = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        # 현재 계정에서 사용 가능한 모든 모델 리스트업
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 2.0 버전 우선 선택, 없으면 리스트의 첫 번째 모델 사용
        selected_model_name = next((m for m in available_models if '2.0' in m), available_models[0])
        model = genai.GenerativeModel(selected_model_name)
        st.sidebar.success(f"✅ 연결된 모델: {selected_model_name}")
    except Exception as e:
        st.sidebar.error(f"⚠️ 모델 연결 실패: {e}")

# 4. 분석 엔진 실행
if st.button(f"🚀 {ticker} 상장 이후 데이터 전수 조사 시작"):
    if not model:
        st.warning("먼저 유효한 Gemini API 키를 입력해 주세요.")
    else:
        with st.spinner(f"데이터를 수집하고 AI가 정밀 분석 중입니다. 잠시만 기다려 주세요..."):
            try:
                # [A] 주가 데이터 수집 (상장 이후 전체)
                stock = yf.Ticker(ticker)
                hist = stock.history(period="max")
                if hist.empty:
                    st.error("티커를 찾을 수 없거나 주가 데이터를 불러올 수 없습니다.")
                    st.stop()

                # [B] 웹 데이터 수집 (MarketBeat/HoldingsChannel 등 다중 탐색)
                url = f"https://www.marketbeat.com/stocks/NASDAQ/{ticker}/institutional-ownership/"
                res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                if res.status_code != 200:
                    url = f"https://www.marketbeat.com/stocks/NYSE/{ticker}/institutional-ownership/"
                    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                soup = BeautifulSoup(res.text, 'html.parser')
                # 3대 기관 키워드 필터링
                target_rows = [row.get_text(strip=True) for
