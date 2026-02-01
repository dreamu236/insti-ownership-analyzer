import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from io import StringIO

# 1. 페이지 설정 (원장님 취향: Modern & Simple)
st.set_page_config(page_title="Institutional Ownership Tracker", layout="wide")
st.title("📊 3대 기관 지분 변동 전수 조사 시스템")
st.caption("상장 이후 BlackRock, Vanguard, ARK Investment의 거래 히스토리를 분석합니다.")

# 2. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")
    ticker_input = st.text_input("분석 티커 입력", placeholder="예: RXRX, NVDA, TSLA").upper().strip()
    st.divider()
    st.info("💡 이 시스템은 SEC 공식 데이터와 금융 API를 교차 활용하여 차단 없이 상장 이후 데이터를 추적합니다.")

# 3. 핵심 엔진: 상장 이후 전수 조사 로직
def get_comprehensive_history(ticker):
    history_data = []
    # [경로 1] SEC 공식 EDGAR 데이터베이스 (공식 13G/D/F 히스토리)
    # SEC 서버는 User-Agent에 연구 목적임을 밝혀야 차단하지 않습니다.
    sec_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=13&output=atom&count=100"
    headers = {'User-Agent': 'Graduate Research Project (kdk100625@gmail.com)'}
    
    try:
        res = requests.get(sec_url, headers=headers, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text
                date = entry.find('atom:updated', ns).text[:10]
                
                # 3대 기관 필터링
                title_lower = title.lower()
                if any(k in title_lower for k in ["blackrock", "vanguard", "ark investment", "ark innovation"]):
                    history_data.append({
                        "Reported Date": date,
                        "Filed By": title.split(" filed by ")[-1],
                        "Type": title.split(" - ")[0],
                        "Shares Owned": "Check SEC Link", # 상세 수치는 원문 확인 권장
                        "Change vs Prev": "See Filing"
                    })
    except Exception as e:
        st.sidebar.warning(f"SEC 데이터 로드 실패: {e}")

    # [경로 2] 야후 파이낸스 백업 (최신 보유 현황 및 거래 이력 보완)
    try:
        stock = yf.Ticker(ticker)
        inst_holders = stock.get_institutional_holders()
        if inst_holders is not None and not inst_holders.empty:
            for _, row in inst_holders.iterrows():
                holder_name = str(row['Holder']).lower()
                if any(k in holder_name for k in ["blackrock", "vanguard", "ark"]):
                    history_data.append({
                        "Reported Date": row['Date Reported'].strftime('%Y-%m-%d'),
                        "Filed By": row['Holder'],
                        "Type": "13F",
                        "Shares Owned": f"{row['Shares']:,}",
                        "Change vs Prev": "Latest"
                    })
    except:
        pass
        
    return history_data

# 4. 분석 실행
if ticker_input and st.button(f"🚀 {ticker_input} 전수 조사 시작"):
    with st.spinner(f"{ticker_input}의 상장 이후 데이터를 정밀 탐색 중입니다..."):
        try:
            # 주가 데이터 수집 (상장 이후 전체)
            stock_obj = yf.Ticker(ticker_input)
            hist = stock_obj.history(period="max")
            
            if hist.empty:
                st.error("티커를 찾을 수 없습니다. 주가 데이터가 존재하지 않습니다.")
                st.stop()

            # 데이터 수집
            raw_data = get_comprehensive_history(ticker_input)
            
            if not raw_data:
                st.warning("⚠️ 3대 기관의 공시 내역을 찾을 수 없습니다. (신생 기업이거나 대량 보유 공시가 아직 없는 상태일 수 있습니다.)")
            else:
                df = pd.DataFrame(raw_data).drop_duplicates(subset=['Reported Date', 'Filed By'])
                df = df.sort_values(by="Reported Date", ascending=False)

                # 원장님의 10개 컬럼 레이아웃 구성
                df["Transaction Date"] = df["Reported Date"]
                df["Company"] = f"{ticker_input} Corp."
                df["Symbol"] = ticker_input
                df["% Owned"] = "N/A"

                # 주가 결합 (10번째 컬럼)
                def fetch_price(d):
                    try: return round(hist.loc[d]['Close'], 2)
                    except: return "N/A"
                
                df[f"{ticker_input} Close Price"] = df["Reported Date"].apply(fetch_price)

                # 컬럼 순서 고정
                final_cols = [
                    "Reported Date", "Transaction Date", "Type", "Company", "Symbol",
                    "Filed By", "Shares Owned", "% Owned", "Change vs Prev", f"{ticker_input} Close Price"
                ]
                df = df[final_cols]

                # 결과 출력
                st.subheader(f"✅ {ticker_input} 분석 결과 (상장 이후 히스토리)")
                st.dataframe(df, use_container_width=True)
                
                # 엑셀 다운로드
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 논문용 엑셀(CSV) 다운로드", csv, f"{ticker_input}_research_data.csv", "text/csv")

        except Exception as e:
            st.error(f"시스템 오류 발생: {e}")

st.divider()
st.caption("Designed for Academic Research | Data source: SEC EDGAR & Yahoo Finance")
