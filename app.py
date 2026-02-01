import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import StringIO
from datetime import datetime
import time

# 1. 페이지 설정
st.set_page_config(page_title="3대 기관 지분 추적기", layout="wide")
st.title("📊 3대 기관(BlackRock, Vanguard, ARK) 거래 히스토리")
st.caption("상장 이후 해당 기관들의 모든 지분 변동 내역을 추출합니다.")

# 2. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")
    ticker_input = st.text_input("분석 티커 입력", placeholder="예: RXRX, NVDA").upper().strip()
    st.info("💡 3대 기관의 상장 이후 거래 내역만 필터링하여 가져옵니다.")

# 3. 데이터 추출 엔진
def fetch_history(ticker):
    # 브라우저처럼 보이게 하는 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # 상장 이후 전체 히스토리가 담긴 URL (거래소 자동 판별)
    url = f"https://www.marketbeat.com/stocks/NASDAQ/{ticker}/institutional-ownership/"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        url = f"https://www.marketbeat.com/stocks/NYSE/{ticker}/institutional-ownership/"
        response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'ownership-history-table'}) # 히스토리 전용 테이블 조준
    
    if not table:
        return None

    rows = []
    # 3대 기관 키워드
    targets = ["blackrock", "vanguard", "ark investment", "ark innovation"]
    
    for tr in table.find_all('tr')[1:]:
        tds = tr.find_all('td')
        if len(tds) >= 5:
            inst_name = tds[1].get_text(strip=True)
            # 3대 기관 데이터만 필터링
            if any(t in inst_name.lower() for t in targets):
                rows.append({
                    "Reported Date": tds[0].get_text(strip=True),
                    "Transaction Date": tds[0].get_text(strip=True),
                    "Type": "13F/G",
                    "Filed By": inst_name,
                    "Shares Owned": tds[2].get_text(strip=True).replace(',', '').replace('$', ''),
                    "Change vs Prev": tds[3].get_text(strip=True).replace(',', ''),
                    "Value": tds[4].get_text(strip=True)
                })
    return rows

# 4. 실행 버튼
if ticker_input and st.button(f"🚀 {ticker_input} 3대 기관 히스토리 전수 조사"):
    with st.spinner(f"{ticker_input}의 3대 기관 데이터를 분석 중..."):
        try:
            # 주가 데이터 (상장 이후 전체)
            stock = yf.Ticker(ticker_input)
            hist = stock.history(period="max")
            
            # 히스토리 수집
            data_rows = fetch_history(ticker_input)
            
            if not data_rows:
                st.warning("3대 기관의 과거 거래 내역을 찾을 수 없습니다.")
            else:
                df = pd.DataFrame(data_rows)
                
                # 10개 컬럼 레이아웃 맞추기
                df["Company"] = f"{ticker_input} Corp."
                df["Symbol"] = ticker_input
                df["% Owned"] = "N/A" # 해당 사이트에서 히스토리별 지분율은 제공하지 않음

                # 주가 결합 (10번째 컬럼)
                def get_close_price(date_str):
                    try:
                        # 날짜 형식 변환 (MM/DD/YYYY -> YYYY-MM-DD)
                        d = datetime.strptime(date_str, '%m/%d/%Y').strftime('%Y-%m-%d')
                        return round(hist.loc[d]['Close'], 2)
                    except: return "N/A"

                df[f"{ticker_input} Close Price"] = df['Reported Date'].apply(get_close_price)

                # 컬럼 순서 재배치 (원장님 요청 10개)
                final_cols = [
                    "Reported Date", "Transaction Date", "Type", "Company", "Symbol",
                    "Filed By", "Shares Owned", "% Owned", "Change vs Prev", f"{ticker_input} Close Price"
                ]
                df = df[final_cols]

                # 결과 출력
                st.subheader(f"✅ {ticker_input} 3대 기관 거래 내역 (상장 이후)")
                st.dataframe(df, use_container_width=True)
                
                # 다운로드
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 엑셀(CSV) 다운로드", csv, f"{ticker_input}_3_inst_history.csv", "text/csv")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("Insti-Ownership Analyzer v3.5 | 3개 기관 전용 필터링 모드")
