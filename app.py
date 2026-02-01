import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from io import StringIO
from datetime import datetime
import time

# 1. 페이지 설정 (심플 & 모던)
st.set_page_config(page_title="Insti-Ownership Analyzer", layout="wide")
st.title("📊 기관 투자자 지분 분석 시스템")

# 2. 사이드바 - 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")
    api_key = st.text_input("Google Gemini API 키 입력", type="password")
    ticker_input = st.text_input("분석 티커 입력", placeholder="예: NVDA, RXRX, GH").upper().strip()
    st.markdown("---")
    st.caption("v2.5 - AI 자동 모델 매칭 및 오류 방지 엔진 탑재")

# 3. 모델 자동 탐색 엔진 (404 오류 원천 차단)
model = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        # 현재 계정에서 사용 가능한 모델 목록 확인
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 2.0 버전 우선, 없으면 1.5, 그것도 없으면 리스트 첫 번째 모델 선택
        target_model = next((m for m in models if '2.0' in m), 
                            next((m for m in models if '1.5' in m), models[0]))
        model = genai.GenerativeModel(target_model)
        st.sidebar.success(f"✅ 연결됨: {target_model}")
    except Exception as e:
        st.sidebar.error(f"⚠️ 모델 연결 실패. 키를 확인하세요.")

# 4. 분석 실행 로직
if ticker_input:
    run_button = st.button(f"🚀 {ticker_input} 데이터 전수 조사 시작")
else:
    st.button("🚀 분석할 티커를 입력해 주세요", disabled=True)
    run_button = False

if run_button:
    if not api_key:
        st.error("먼저 Gemini API 키를 입력해야 합니다.")
    else:
        with st.spinner(f"{ticker_input}의 상장 이후 모든 데이터를 추적 중입니다..."):
            try:
                # [A] 주가 데이터 수집 (상장 이후 전체)
                stock = yf.Ticker(ticker_input)
                hist = stock.history(period="max")
                if hist.empty:
                    st.error(f"티커 '{ticker_input}'를 찾을 수 없습니다.")
                    st.stop()

                # [B] 웹 데이터 수집 (다중 경로 탐색)
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                target_rows = []
                # 분석 대상 사이트 후보
                search_urls = [
                    f"https://www.marketbeat.com/stocks/NASDAQ/{ticker_input}/institutional-ownership/",
                    f"https://www.marketbeat.com/stocks/NYSE/{ticker_input}/institutional-ownership/"
                ]

                for url in search_urls:
                    try:
                        res = requests.get(url, headers=headers, timeout=10)
                        if res.status_code == 200:
                            soup = BeautifulSoup(res.text, 'html.parser')
                            for tr in soup.find_all('tr'):
                                text = tr.get_text(" ", strip=True)
                                # 3대 기관 키워드 포함 시 수집
                                if any(k in text.lower() for k in ["blackrock", "vanguard", "ark investment", "ark innovation"]):
                                    target_rows.append(text)
                            if target_rows: break
                    except: continue

                if not target_rows:
                    st.warning("최근 공시된 3대 기관의 데이터를 사이트에서 찾을 수 없습니다. (보안 차단 또는 데이터 없음)")
                    st.stop()

                # [C] AI 정제 (10개 컬럼 레이아웃 강제)
                prompt = f"""
                Analyze the following institutional ownership data for {ticker_input}.
                Create a CSV table with EXACTLY these 9 columns:
                Reported Date, Transaction Date, Type, Company, Symbol, Filed By, Shares Owned, % Owned, Change vs Prev
                
                Data to parse: {target_rows[:40]}
                
                Rules:
                - Date: YYYY-MM-DD
                - Company: {ticker_input} Corp.
                - Symbol: {ticker_input}
                - Type: Always '13G/F'
                - Shares Owned: Number only (no commas)
                """
                
                response = model.generate_content(prompt)
                csv_clean = response.text.replace('```csv', '').replace('```', '').strip()
                df = pd.read_csv(StringIO(csv_clean))

                # [D] 주가 결합 (10번째 컬럼)
                def get_price(d_str):
                    try:
                        dt = datetime.strptime(str(d_str).strip(), '%Y-%m-%d').strftime('%Y-%m-%d')
                        return round(hist.loc[dt]['Close'], 2)
                    except: return "N/A"

                df[f"{ticker_input} Close Price"] = df['Transaction Date'].apply(get_price)

                # 5. 최종 결과 출력
                st.subheader(f"✅ {ticker_input} 분석 결과 (10개 컬럼)")
                st.dataframe(df, use_container_width=True)
                
                # 엑셀 다운로드
                csv_file = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 엑셀(CSV) 파일 내려받기", csv_file, f"{ticker_input}_final_data.csv", "text/csv")

            except Exception as e:
                st.error(f"분석 중 예상치 못한 오류가 발생했습니다: {e}")

st.divider()
st.caption("Insti-Ownership Analyzer | Designed for Academic Research & Corporate Strategy")
