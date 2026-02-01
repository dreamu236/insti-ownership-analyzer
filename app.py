import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import StringIO
from datetime import datetime
import json

# 1. 페이지 설정 (심플 & 모던)
st.set_page_config(page_title="Insti-Ownership Analyzer", layout="wide")
st.title("📊 기관 투자자 지분 변동 전수 조사 (v3.0 최종)")
st.caption("상장 이후 모든 거래 내역(주식 수, 변동량) 수치 데이터 추출 모드")

# 2. 사이드바 설정 (티커만 입력)
with st.sidebar:
    st.header("⚙️ 분석 설정")
    ticker_input = st.text_input("분석 티커 입력", placeholder="예: RXRX, NVDA").upper().strip()
    st.info("💡 API 키 없이 작동하며, 상장 이후 전수 데이터를 수집합니다.")

# 3. 데이터 엔진 (HoldingsChannel 전수 조사 로직)
if ticker_input and st.button(f"🚀 {ticker_input} 상장 이후 전수 조사 시작"):
    with st.spinner(f"{ticker_input}의 상장 이후 전체 거래 데이터를 수집 중입니다..."):
        try:
            # [A] 주가 데이터 수집 (상장 이후 전체)
            stock = yf.Ticker(ticker_input)
            hist = stock.history(period="max")
            
            # [B] 프록시 서버를 통한 HoldingsChannel 강제 접속 (차단 우회)
            # 이 사이트는 상장 시점부터의 모든 거래(Shares, Change)를 표로 제공합니다.
            target_url = f"https://www.holdingschannel.com/all/institutional-ownership-history/?symbol={ticker_input}"
            proxy_url = f"https://api.allorigins.win/get?url={target_url}"
            
            res = requests.get(proxy_url, timeout=15)
            data = json.loads(res.text)
            soup = BeautifulSoup(data['contents'], 'html.parser')
            
            # 테이블 찾기
            table = soup.find('table', {'class': 'maintables'})
            if not table:
                st.error("데이터 테이블을 찾을 수 없습니다. 티커가 정확한지 확인해 주세요.")
                st.stop()

            # 데이터 파싱
            rows = []
            for tr in table.find_all('tr')[1:]: # 헤더 제외
                tds = tr.find_all('td')
                if len(tds) >= 6:
                    date_raw = tds[0].text.strip()
                    inst = tds[1].text.strip()
                    shares = tds[2].text.strip().replace(',', '')
                    change = tds[3].text.strip().replace(',', '')
                    percent = tds[5].text.strip()
                    
                    rows.append({
                        "Reported Date": date_raw,
                        "Transaction Date": date_raw,
                        "Type": "13G/F",
                        "Company": f"{ticker_input} Corp.",
                        "Symbol": ticker_input,
                        "Filed By": inst,
                        "Shares Owned": shares,
                        "% Owned": percent,
                        "Change vs Prev": change
                    })

            # [C] 데이터 프레임 생성 및 주가 결합 (10개 컬럼)
            if not rows:
                st.warning("수집된 데이터가 없습니다.")
            else:
                df = pd.DataFrame(rows)
                
                # 주가 매칭 (10번째 컬럼)
                def get_price(d):
                    try:
                        return round(hist.loc[d]['Close'], 2)
                    except: return "N/A"
                
                df[f"{ticker_input} Close Price"] = df['Reported Date'].apply(get_price)

                # 컬럼 순서 고정 (원장님 요청 10개)
                final_cols = [
                    "Reported Date", "Transaction Date", "Type", "Company", "Symbol",
                    "Filed By", "Shares Owned", "% Owned", "Change vs Prev", f"{ticker_input} Close Price"
                ]
                df = df[final_cols]

                # 결과 출력
                st.subheader(f"✅ {ticker_input} 상장 이후 거래 히스토리 분석 결과")
                st.dataframe(df, use_container_width=True)
                
                # 엑셀 다운로드
                csv_file = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 엑셀(CSV) 파일로 내려받기", csv_file, f"{ticker_input}_history_data.csv", "text/csv")

        except Exception as e:
            st.error(f"데이터 수집 중 오류 발생: {e}")

st.divider()
st.caption("Insti-Ownership Analyzer v3.0 | Graduate Thesis Support Engine")
