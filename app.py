import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="Institutional Ownership History", layout="wide")
st.title("📊 3대 기관 상장 이후 전수 조사 (수치 완본)")

with st.sidebar:
    ticker = st.text_input("티커 입력", placeholder="예: RXRX, NVDA").upper().strip()

if ticker and st.button(f"🚀 {ticker} 상장 이후 모든 거래 데이터 가져오기"):
    with st.spinner("과거 데이터를 역추적 중입니다..."):
        try:
            # 1. 주가 데이터 (상장 이후 전체)
            stock = yf.Ticker(ticker)
            hist = stock.history(period="max")
            
            # 2. 히스토리 데이터 수집 (HoldingsChannel 전수 조사 페이지)
            # 이 주소는 상장 시점부터 모든 분기의 숫자를 한 표에 보여줍니다.
            url = f"https://www.holdingschannel.com/history/?symbol={ticker}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            
            res = requests.get(url, headers=headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table', {'class': 'maintables'}) # 메인 수치 테이블 타겟팅

            if not table:
                st.error("사이트 차단으로 데이터를 읽지 못했습니다. 잠시 후 다시 시도해 주세요.")
                st.stop()

            rows = []
            # 3대 기관 키워드
            targets = ["blackrock", "vanguard", "ark investment", "ark innovation"]

            for tr in table.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 6:
                    inst_name = tds[1].get_text(strip=True)
                    if any(t in inst_name.lower() for t in targets):
                        rows.append({
                            "Reported Date": tds[0].get_text(strip=True),
                            "Filed By": inst_name,
                            "Shares Owned": tds[2].get_text(strip=True).replace(',', ''),
                            "Change vs Prev": tds[3].get_text(strip=True).replace(',', ''),
                            "% Owned": tds[5].get_text(strip=True)
                        })

            if not rows:
                st.warning("해당 3대 기관의 공시 내역이 발견되지 않았습니다.")
            else:
                df = pd.DataFrame(rows)
                df["Transaction Date"] = df["Reported Date"]
                df["Type"] = "13F/G"
                df["Company"] = f"{ticker} Corp."
                df["Symbol"] = ticker

                # 주가 결합
                def get_price(d_str):
                    try:
                        d = pd.to_datetime(d_str).strftime('%Y-%m-%d')
                        return round(hist.loc[d]['Close'], 2)
                    except: return "N/A"

                df[f"{ticker} Close Price"] = df['Reported Date'].apply(get_price)

                # 원장님 요청 10개 컬럼 레이아웃 고정
                final_cols = ["Reported Date", "Transaction Date", "Type", "Company", "Symbol", 
                              "Filed By", "Shares Owned", "% Owned", "Change vs Prev", f"{ticker} Close Price"]
                df = df[final_cols]

                st.subheader(f"✅ {ticker} 상장 이후 3대 기관 거래 현황")
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 논문용 엑셀(CSV) 다운로드", csv, f"{ticker}_history.csv", "text/csv")

        except Exception as e:
            st.error(f"오류 발생: {e}")
