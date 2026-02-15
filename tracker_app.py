from datetime import datetime, date
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

import gspread
from google.oauth2.service_account import Credentials


# ----------------------------
# Google Sheets helpers
# ----------------------------
@st.cache_resource
def get_gsheets_client():
    creds_dict = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def open_sheet():
    gc = get_gsheets_client()
    spreadsheet_id = st.secrets["sheets"]["spreadsheet_id"]
    return gc.open_by_key(spreadsheet_id)

def append_row(sheet_name: str, row_values: list):
    sh = open_sheet()
    ws = sh.worksheet(sheet_name)
    ws.append_row(row_values, value_input_option="USER_ENTERED")

def read_df(sheet_name: str) -> pd.DataFrame:
    sh = open_sheet()
    ws = sh.worksheet(sheet_name)
    records = ws.get_all_records()  # uses row1 as header
    return pd.DataFrame(records)


# ----------------------------
# UI
# ----------------------------
st.set_page_config(page_title="감량 코치 트래커", layout="wide")
st.title("감량 코치 트래커 (Google Sheets 영구 저장)")

tab1, tab2, tab3 = st.tabs(["✅ 오늘 기록", "📊 대시보드", "🗂 데이터 보기/백업"])


with tab1:
    st.subheader("1) 체중/허리/컨디션 기록")
    colA, colB, colC, colD = st.columns(4)

    with colA:
        d = st.date_input("날짜", value=date.today())
        weight = st.number_input("체중(kg)", min_value=0.0, step=0.1, value=0.0)
    with colB:
        waist = st.number_input("허리둘레(cm) (없으면 0)", min_value=0.0, step=0.5, value=0.0)
        sleep_h = st.number_input("수면(시간)", min_value=0.0, step=0.5, value=7.0)
    with colC:
        condition = st.slider("컨디션(1~5)", 1, 5, 3)
        alcohol = st.selectbox("음주", ["없음", "1~2잔", "소주 1병", "소주 1병 이상"])
    with colD:
        if st.button("체중/컨디션 저장"):
            try:
                append_row(
                    "weight",
                    [
                        datetime.now().isoformat(timespec="seconds"),
                        d.isoformat(),
                        float(weight),
                        float(waist),
                        float(sleep_h),
                        int(condition),
                        alcohol,
                    ],
                )
                st.success("저장 완료! (Google Sheets)")
            except Exception as e:
                st.error(f"저장 실패: {e}")

    st.divider()
    st.subheader("2) 식단 기록 (카톡처럼 한 줄로 붙여넣기 가능)")
    meal_slot = st.selectbox("식사 구간", ["출근 전", "근무 중", "운동 전", "운동 후", "기타"])
    items = st.text_area("먹은 것(자유 입력)", placeholder="예) 위트빅스 3조각 + 프로틴 1스쿱, 햄 200g, 계란 3개")
    meal_notes = st.text_input("메모(선택)", placeholder="예) 저탄수일 / 술자리 / 외식")

    if st.button("식단 저장"):
        if items.strip() == "":
            st.error("먹은 것을 입력해줘.")
        else:
            try:
                append_row(
                    "meals",
                    [
                        datetime.now().isoformat(timespec="seconds"),
                        d.isoformat(),
                        meal_slot,
                        items.strip(),
                        meal_notes.strip(),
                    ],
                )
                st.success("식단 저장 완료! (Google Sheets)")
            except Exception as e:
                st.error(f"저장 실패: {e}")

    st.divider()
    st.subheader("3) 운동 기록")
    wtype = st.selectbox("운동 종류", ["상체", "하체", "전신", "유산소", "휴식"])
    duration = st.number_input("운동 시간(분)", min_value=0, step=5, value=60)
    wnotes = st.text_input("운동 메모(선택)", placeholder="예) 스쿼트 170, 데드 220 / 인터벌 10분")

    if st.button("운동 저장"):
        try:
            append_row(
                "workouts",
                [
                    datetime.now().isoformat(timespec="seconds"),
                    d.isoformat(),
                    wtype,
                    int(duration),
                    wnotes.strip(),
                ],
            )
            st.success("운동 저장 완료! (Google Sheets)")
        except Exception as e:
            st.error(f"저장 실패: {e}")


with tab2:
    st.subheader("📊 대시보드")

    try:
        wdf = read_df("weight")
        mdf = read_df("meals")
        odf = read_df("workouts")
    except Exception as e:
        st.error(f"시트 읽기 실패: {e}")
        st.stop()

    if not wdf.empty:
        # type conversion
        wdf["date"] = pd.to_datetime(wdf["date"], errors="coerce")
        wdf["weight_kg"] = pd.to_numeric(wdf.get("weight_kg"), errors="coerce")
        wdf["waist_cm"] = pd.to_numeric(wdf.get("waist_cm"), errors="coerce")
        wdf = wdf.sort_values("date")

        wdf["w7"] = wdf["weight_kg"].rolling(window=7, min_periods=1).mean()

        col1, col2, col3 = st.columns(3)
        latest = wdf.dropna(subset=["weight_kg"]).tail(1)
        if not latest.empty:
            col1.metric("최근 체중(kg)", f"{float(latest['weight_kg'].iloc[0]):.1f}")
            col2.metric("최근 7일 평균(kg)", f"{float(latest['w7'].iloc[0]):.1f}")
        if wdf["waist_cm"].dropna().shape[0] > 0:
            col3.metric("최근 허리(cm)", f"{float(wdf['waist_cm'].dropna().iloc[-1]):.1f}")

        fig = plt.figure()
        plt.plot(wdf["date"], wdf["weight_kg"], marker="o")
        plt.plot(wdf["date"], wdf["w7"])
        plt.title("체중 추세 (7일 평균 포함)")
        plt.xlabel("date")
        plt.ylabel("kg")
        st.pyplot(fig)

        if wdf["waist_cm"].dropna().shape[0] > 0:
            fig2 = plt.figure()
            plt.plot(wdf["date"], wdf["waist_cm"], marker="o")
            plt.title("허리둘레 추세")
            plt.xlabel("date")
            plt.ylabel("cm")
            st.pyplot(fig2)
    else:
        st.info("아직 체중/컨디션 데이터가 없어. '오늘 기록' 탭에서 먼저 저장해줘.")

    st.divider()
    st.subheader("🧾 최근 기록 요약")
    colA, colB = st.columns(2)
    with colA:
        st.caption("최근 식단 10개")
        st.dataframe(mdf.tail(10), use_container_width=True)
    with colB:
        st.caption("최근 운동 10개")
        st.dataframe(odf.tail(10), use_container_width=True)


with tab3:
    st.subheader("🗂 구글 시트에 저장됩니다")
    st.write("현재 연결된 spreadsheet_id:")
    st.code(st.secrets["sheets"]["spreadsheet_id"])

    st.write("저장되는 시트 탭 이름:")
    st.code("weight\nmeals\nworkouts")

    st.info("백업은 Google Sheets에서 파일 → 다운로드로 언제든지 할 수 있어요.")
