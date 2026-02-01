import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="Insti-Ownership Analyzer", layout="wide")
st.title("📊 기관 투자자 지분 분석 시스템 (v2.1)")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ 분석 설정")
    api_key = st.text_input("Google Gemini API 키", type="password")
    ticker = st.text_input("분석 티커 입력", "RXRX").upper()

model = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        selected_model_name = next((m for m in available_models if '2.0' in m), available_models[0])
        model = genai.GenerativeModel(selected_model_name)
        st.sidebar.success(f"✅ 연결됨: {selected_model_name}")
    except Exception as e:
        st.sidebar.error(f"⚠️ 연결 실패: {e}")

if st.button(f"🚀 {ticker} 데이터 전수 조사 시작"):
    if not model:
        st.warning("API 키를 입력해 주세요.")
    else:
        with st.spinner(f"분석 중..."):
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="max")
                
                url = f"https://www.marketbeat.com/stocks/NASDAQ/{ticker}/institutional-ownership/"
                res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                if res.status_code != 200:
                    url = f"https://www.marketbeat.com/stocks/NYSE/{ticker}/institutional-ownership/"
                    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # 오류 수정된 데이터 수집 로직
                target_rows = []
                for row in soup.find_all('tr'):
                    row_text = row.get_text(strip=True)
                    if any(inst in row_text for inst in ["BlackRock", "Vanguard", "ARK Investment"]):
                        target_rows.append(row_text)

                if not target_rows:
                    st.info("해당 기관의 데이터를 찾을 수 없습니다.")
                    st.stop()

                prompt = f"Convert to CSV with 9 headers: Reported Date, Transaction Date, Type, Company, Symbol, Filed By, Shares Owned, % Owned, Change vs Prev. Data: {target_rows[:30]}"
                response = model.generate_content(prompt)
                csv_clean = response.text.replace('```csv', '').replace('```', '').strip()
                df = pd.read_csv(StringIO(csv_clean))

                def get_price(date_str):
                    try:
                        dt = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
                        return round(hist.loc[dt]['Close'], 2)
                    except: return "N/A"

                df[f"{ticker} Close Price"] = df['Transaction Date'].apply(get_price)
                st.dataframe(df, use_container_width=True)
                
                csv_export = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 엑셀(CSV) 내려받기", csv_export, f"{ticker}_data.csv", "text/csv")

            except Exception as e:
                st.error(f"오류: {e}")
