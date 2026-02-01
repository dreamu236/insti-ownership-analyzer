import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import StringIO
from datetime import datetime
import time

# 1. 페이지 설정
st.set_page_config(page_title="3대 기관 지분 전수 분석기", layout="wide")
st.title("📊 3대 기관 상장 이후 거래 히스토리 추출")
st.caption("BlackRock, Vanguard, ARK Investment의 상장 이후 모든 수치 데이터를 추적합니다.")

# 2. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")
    ticker_input = st.text_input("분석 티커 입력", placeholder="예: RXRX, NVDA").upper().strip()
    st.info("💡 이 도구는 상장 이후 모든 히스토리를 전수 조사합니다.")

# 3. 데이터 추출 엔진 (v4.0 고도화 버전)
def fetch_institutional_history(ticker):
    # 보안 차단을 피하기 위한 고도화된 브라우저 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/'
    }
    
    # 상장 이후 전체 히스토리 페이지 타겟팅
    url = f"https://www.holdingschannel.com/history/?symbol={ticker}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        # 테이블 ID에 의존하지 않고 모든 테이블 스캔
        tables = soup.find_all('table')
        
        rows = []
        # 3대 기관 키워드 (대소문자 무관)
        targets = ["blackrock", "vanguard", "ark investment", "ark innovation"]

        for table in tables:
            for tr in table.find_all('tr'):
                text = tr.get_text().lower()
                if any(t in text for t in targets):
                    tds = tr.find_all('td')
                    if len(tds) >= 5:
                        rows.append({
                            "Date": tds[0].get_text(strip=True),
                            "Institution": tds[1].get_text(strip=True),
                            "Shares": tds[2].get_text(strip=True).replace(',', ''),
                            "Change": tds[3].get_text(strip=True).replace(',', ''),
                            "Value": tds[4].get_text(strip=True)
                        })
        return rows
    except:
        return None

# 4. 분석 실행
if ticker_input and st.button(f"🚀 {ticker_input} 전수 조사 시작"):
    with st.spinner(f"{ticker_input}의 상장 이후 데이터를 정밀 스캔 중입니다..."):
        try:
            # 주가 데이터 수집
            stock = yf.Ticker(ticker_input)
            hist = stock.history(period="max")
            
            # 히스토리 수집
            raw_data = fetch_institutional_history(ticker_input)
            
            if not raw_data:
                st.warning("⚠️ 데이터를 수집하지 못했습니다. 보안 차단 혹은 해당 기관의 데이터가 없을 수 있습니다.")
            else:
                df = pd.DataFrame(raw_data)
                
                # 원장님의 10개 컬럼 레이아웃 구성
                df["Reported Date"] = df["Date"]
                df["Transaction Date"] = df["Date"]
                df["Type"] = "13F/G"
                df["Company"] = f"{ticker_input} Corp."
                df["Symbol"] = ticker_input
                df["Filed By"] = df["Institution"]
                df["Shares Owned"] = df["Shares"]
                df["% Owned"] = "N/A"
                df["Change vs Prev"] = df["Change"]

                # 주가 결합 (10번째 컬럼)
                def match_price(date_str):
                    try:
                        # 날짜 형식 보정 (YYYY-MM-DD)
                        d = pd.to_datetime(date_str).strftime('%Y-%m-%d')
                        return round(hist.loc[d]['Close'], 2)
                    except: return "N/A"

                df[f"{ticker_input} Close Price"] = df['Reported Date'].apply(match_price)

                # 최종 컬럼 순서 고정
                final_cols = [
                    "Reported Date", "Transaction Date", "Type", "Company", "Symbol",
                    "Filed By", "Shares Owned", "% Owned", "Change vs Prev", f"{ticker_input} Close Price"
                ]
                df = df[final_cols]

                # 결과 출력
                st.subheader(f"✅ {ticker_input} 3대 기관 거래 현황 (상장 이후)")
                st.dataframe(df, use_container_width=True)
                
                # 다운로드 버튼
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 엑셀(CSV) 다운로드", csv, f"{ticker_input}_history.csv", "text/csv")

        except Exception as e:
            st.error(f"오류 발생: {e}")

st.divider()
st.caption("Insti-Ownership Analyzer v4.0 | 상장 이후 전수 조사 최적화")
