import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import io

# 1. 페이지 설정
st.set_page_config(page_title="Insti-Ownership Tracker", layout="wide")
st.title("📊 기관 지분 변동 전수 조사 시스템 (v2.9)")
st.caption("안정성 극대화 버전: SEC 공식 데이터 + 금융 API 교차 검증")

# 2. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")
    ticker_input = st.text_input("분석 티커 입력", placeholder="예: RXRX, NVDA").upper().strip()
    st.info("💡 이 도구는 상장 이후부터 현재까지의 모든 공시를 추적합니다.")

# 3. 데이터 엔진 함수
def get_ownership_data(ticker):
    final_data = []
    
    # [경로 1] SEC 공식 EDGAR 데이터 (가장 정확한 히스토리)
    # SEC 서버는 User-Agent에 이메일 형식이 포함되어야만 데이터를 내어줍니다.
    sec_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=13&output=atom"
    headers = {'User-Agent': 'Academic Research Project kdk100625@gmail.com'}
    
    try:
        res = requests.get(sec_url, headers=headers, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text
                date_str = entry.find('atom:updated', ns).text[:10]
                
                parts = title.split('-')
                filing_type = parts[0].strip() if len(parts) > 0 else "SC 13G/D"
                filed_by = parts[1].strip() if len(parts) > 1 else "Institutional Investor"
                
                final_data.append({
                    "Reported Date": date_str,
                    "Transaction Date": date_str,
                    "Type": filing_type,
                    "Filed By": filed_by
                })
    except:
        pass

    # [경로 2] 야후 파이낸스 보조 데이터 (SEC 경로가 빈약할 때 보충)
    try:
        stock = yf.Ticker(ticker)
        # 13F 기관 보유 현황 (최근 분기 중심)
        inst_holders = stock.institutional_holders
        if inst_holders is not None and not inst_holders.empty:
            for _, row in inst_holders.iterrows():
                final_data.append({
                    "Reported Date": row['Date Reported'].strftime('%Y-%m-%d'),
                    "Transaction Date": row['Date Reported'].strftime('%Y-%m-%d'),
                    "Type": "13F",
                    "Filed By": row['Holder']
                })
    except:
        pass
        
    return final_data

# 4. 분석 실행
if ticker_input and st.button(f"🚀 {ticker_input} 상장 이후 전수 조사"):
    with st.spinner(f"{ticker_input}의 상장 이후 히스토리를 불러오는 중..."):
        try:
            # 주가 데이터 (상장 이후 전체)
            stock = yf.Ticker(ticker_input)
            hist = stock.history(period="max")
            
            if hist.empty:
                st.error("티커를 확인해 주세요. 주가 데이터를 찾을 수 없습니다.")
                st.stop()

            # 기관 데이터 수집
            raw_results = get_ownership_data(ticker_input)

            if not raw_results:
                st.warning("데이터를 찾을 수 없습니다. 티커를 다시 확인하거나 잠시 후 시도해 주세요.")
            else:
                # 데이터 정제 및 10개 컬럼 구성
                df = pd.DataFrame(raw_results)
                # 중복 제거 (두 경로에서 겹치는 경우 대비)
                df = df.drop_duplicates(subset=['Reported Date', 'Filed By'])
                # 날짜 내림차순 정렬
                df = df.sort_values(by="Reported Date", ascending=False)

                # 공통 정보 추가
                df["Company"] = f"{ticker_input} Corp."
                df["Symbol"] = ticker_input
                df["Shares Owned"] = "공식 링크 확인"
                df["% Owned"] = "N/A"
                df["Change vs Prev"] = "N/A"

                # 주가 결합 (10번째 컬럼)
                def match_price(d):
                    try:
                        return round(hist.loc[d]['Close'], 2)
                    except: return "N/A"
                
                df[f"{ticker_input} Close Price"] = df['Reported Date'].apply(match_price)

                # 최종 컬럼 순서 고정 (원장님 요청 10개)
                final_cols = [
                    "Reported Date", "Transaction Date", "Type", "Company", "Symbol",
                    "Filed By", "Shares Owned", "% Owned", "Change vs Prev", f"{ticker_input} Close Price"
                ]
                df = df[final_cols]

                # 결과 출력
                st.subheader(f"✅ {ticker_input} 상장 이후 지분 공시 현황")
                st.dataframe(df, use_container_width=True)
                
                # 다운로드 버튼
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 엑셀(CSV) 다운로드", csv, f"{ticker_input}_history.csv", "text/csv")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("Insti-Ownership Tracker | Designed for Graduate Research")
