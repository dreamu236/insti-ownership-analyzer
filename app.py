import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="Thesis Data Master v5.0", layout="wide")
st.title("🎓 논문용 3대 기관 지분 변동 전수 조사")
st.info("💡 개인 PC에서 실행 시 차단 없이 가장 정확한 데이터를 수집합니다.")

ticker = st.text_input("분석할 티커를 입력하세요", placeholder="예: RXRX, NVDA").upper().strip()

if ticker and st.button(f"🚀 {ticker} 상장 이후 3대 기관 전수 조사"):
    with st.spinner("데이터를 정밀하게 추출 중입니다..."):
        try:
            # 1. 주가 데이터 (상장 이후 전체)
            stock = yf.Ticker(ticker)
            hist = stock.history(period="max")
            
            # 2. 거래 히스토리 수집 (차단 방지를 위한 정밀 헤더)
            url = f"https://www.holdingschannel.com/history/?symbol={ticker}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            }
            
            res = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table', {'class': 'maintables'})

            if not table:
                st.error("데이터 테이블을 찾을 수 없습니다. (현재 IP에서 접근이 제한되었을 수 있습니다.)")
                st.stop()

            rows = []
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
                st.warning("해당 기관의 거래 내역을 찾을 수 없습니다.")
            else:
                df = pd.DataFrame(rows)
                df["Transaction Date"] = df["Reported Date"]
                df["Type"] = "13F/G"
                df["Company"] = f"{ticker} Corp."
                df["Symbol"] = ticker

                # 주가 결합 로직
                def get_price(d_str):
                    try:
                        d = pd.to_datetime(d_str).strftime('%Y-%m-%d')
                        return round(hist.loc[d]['Close'], 2)
                    except: return "N/A"

                df[f"{ticker} Close Price"] = df['Reported Date'].apply(get_price)

                # 최종 10개 컬럼 레이아웃
                final_cols = ["Reported Date", "Transaction Date", "Type", "Company", "Symbol", 
                              "Filed By", "Shares Owned", "% Owned", "Change vs Prev", f"{ticker} Close Price"]
                df = df[final_cols]

                st.subheader(f"✅ {ticker} 분석 결과")
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 논문용 엑셀(CSV) 다운로드", csv, f"{ticker}_data.csv", "text/csv")

        except Exception as e:
            st.error(f"오류: {e}")
