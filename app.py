import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 페이지 설정 (심플 & 모던)
st.set_page_config(page_title="Insti-Ownership Analyzer (No-API)", layout="wide")
st.title("📊 기관 지분 변동 전수 조사 (No-API 버전)")
st.caption("SEC 공식 데이터 기반 | 상장 이후 전체 공시 히스토리 추출")

# 2. 사이드바 설정 (티커만 입력)
with st.sidebar:
    st.header("⚙️ 분석 설정")
    ticker_input = st.text_input("분석 티커 입력", placeholder="예: RXRX, NVDA, TSLA").upper().strip()
    st.info("💡 이 버전은 API 키 없이 작동합니다.")

# 3. 데이터 수집 및 분석 엔진
if ticker_input and st.button(f"🚀 {ticker_input} 데이터 전수 조사 시작"):
    with st.spinner(f"{ticker_input}의 상장 이후 공시 데이터를 SEC에서 직접 가져오고 있습니다..."):
        try:
            # [A] 주가 데이터 수집 (상장 이후 전체)
            stock = yf.Ticker(ticker_input)
            hist = stock.history(period="max")
            
            if hist.empty:
                st.error("티커를 찾을 수 없거나 주가 데이터가 없습니다.")
                st.stop()

            # [B] SEC 공식 EDGAR 데이터 접속 (13G/D/F 공시 목록)
            # SEC는 공식적으로 공개된 데이터이므로 API 키 없이 브라우저 정보만 있으면 접근 가능합니다.
            sec_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker_input}&type=13&output=atom"
            headers = {'User-Agent': 'Academic Research Project (kdk100625@gmail.com)'}
            res = requests.get(sec_url, headers=headers)
            
            if res.status_code != 200:
                st.error("SEC 서버 접속에 실패했습니다. (나중에 다시 시도해 주세요)")
                st.stop()

            # [C] SEC XML 데이터 수동 파싱 (AI 없이 직접 추출)
            root = ET.fromstring(res.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)

            final_data = []
            for entry in entries:
                title = entry.find('atom:title', ns).text  # 예: "13G - BlackRock Inc."
                date_str = entry.find('atom:updated', ns).text[:10] # YYYY-MM-DD
                link = entry.find('atom:link', ns).attrib['href']
                
                # 제목에서 기관명과 공시 종류 분리 로직
                parts = title.split('-')
                filing_type = parts[0].strip() if len(parts) > 0 else "13G/F"
                filed_by = parts[1].strip() if len(parts) > 1 else "Unknown Institution"

                # 주가 매칭
                try:
                    price = round(hist.loc[date_str]['Close'], 2)
                except:
                    price = "N/A"

                # 원장님의 10개 컬럼 레이아웃에 맞춤
                final_data.append({
                    "Reported Date": date_str,
                    "Transaction Date": date_str, # 공시일 기준으로 우선 설정
                    "Type": filing_type,
                    "Company": f"{ticker_input} Corp.",
                    "Symbol": ticker_input,
                    "Filed By": filed_by,
                    "Shares Owned": "Check Link", # 구체적 주식수는 링크 확인 권장
                    "% Owned": "N/A",
                    "Change vs Prev": "Check Link",
                    f"{ticker_input} Close Price": price
                })

            if not final_data:
                st.warning("상장 이후 공시된 기관 지분 변동 내역을 찾을 수 없습니다.")
            else:
                # 데이터프레임 변환
                df = pd.DataFrame(final_data)
                
                # 컬럼 순서 고정 (원장님 요청 10개 컬럼)
                column_order = [
                    "Reported Date", "Transaction Date", "Type", "Company", "Symbol",
                    "Filed By", "Shares Owned", "% Owned", "Change vs Prev", f"{ticker_input} Close Price"
                ]
                df = df[column_order]

                # 결과 출력
                st.subheader(f"✅ {ticker_input} 상장 이후 지분 공시 히스토리 (전수 조사)")
                st.dataframe(df, use_container_width=True)
                
                # 엑셀 다운로드
                csv_file = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 엑셀(CSV) 파일 내려받기", csv_file, f"{ticker_input}_sec_history.csv", "text/csv")
                
                st.info("💡 각 행의 세부 수치는 SEC 링크를 통해 공식 문서를 확인하는 것이 논문 작성 시 가장 정확합니다.")

        except Exception as e:
            st.error(f"데이터 처리 중 오류 발생: {e}")

st.divider()
st.caption("Insti-Ownership Analyzer v2.8 (No-API) | 데이터 출처: SEC EDGAR & Yahoo Finance")
