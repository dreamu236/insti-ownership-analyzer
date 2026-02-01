import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from io import StringIO

# 페이지 설정
st.set_page_config(page_title="Insti-Ownership Analyzer", layout="wide")
st.title("📊 기관 투자자 지분 분석 시스템")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Google Gemini API 키", type="password", help="Google AI Studio에서 발급받은 키를 입력하세요.")
    ticker = st.text_input("분석 티커 (예: RXRX)", "RXRX").upper()

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

# 메인 버튼
if st.button(f"🚀 {ticker} 데이터 전수 조사 시작"):
    if not api_key:
        st.warning("먼저 Gemini API 키를 입력해 주세요.")
    else:
        with st.spinner(f"{ticker}의 상장 이후 데이터를 수집하고 AI가 정제 중입니다..."):
            try:
                # 1. 주가 데이터 (yfinance)
                stock = yf.Ticker(ticker)
                hist = stock.history(period="max")
                
                # 2. 웹 데이터 수집 (안정적 경로)
                url = f"https://www.marketbeat.com/stocks/NASDAQ/{ticker}/institutional-ownership/"
                res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                if res.status_code != 200:
                    url = f"https://www.marketbeat.com/stocks/NYSE/{ticker}/institutional-ownership/"
                    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                soup = BeautifulSoup(res.text, 'html.parser')
                rows = [row.get_text(strip=True) for row in soup.find_all('tr') if any(x in row.get_text() for x in ["BlackRock", "Vanguard", "ARK"])]

                # 3. AI 정제 (10개 컬럼 고정)
                prompt = f"""
                Analyze the following institutional ownership data for {ticker}.
                Parse it into a CSV format with exactly these 9 headers:
                Reported Date, Transaction Date, Type, Company, Symbol, Filed By, Shares Owned, % Owned, Change vs Prev
                
                Data: {rows[:30]} # 최신 30건 우선 분석
                
                Rules:
                - Date: YYYY-MM-DD
                - Company: {ticker} Corp.
                - Symbol: {ticker}
                - Type: 13G/F
                - No commas in 'Shares Owned'
                """
                
                response = model.generate_content(prompt)
                df = pd.read_csv(StringIO(response.text.replace('```csv', '').replace('```', '').strip()))
                
                # 4. 주가 결합 (10번째 컬럼)
                def fetch_price(d):
                    try: return round(hist.loc[d]['Close'], 2)
                    except: return "N/A"
                
                df[f"{ticker} Close Price"] = df['Transaction Date'].apply(fetch_price)
                
                # 최종 출력
                st.subheader(f"✅ {ticker} 분석 결과 (10개 컬럼)")
                st.dataframe(df, use_container_width=True)
                
                # 다운로드
                csv_data = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 엑셀(CSV)로 내려받기", csv_data, f"{ticker}_analysis.csv", "text/csv")
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("디자인 원칙: Modern, Simple, Data-driven")
