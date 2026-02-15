import os
from datetime import datetime, date
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

APP_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(APP_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

MEALS_CSV = os.path.join(DATA_DIR, "meals.csv")
WORKOUTS_CSV = os.path.join(DATA_DIR, "workouts.csv")
WEIGHT_CSV = os.path.join(DATA_DIR, "weight.csv")


def _init_csv(path: str, columns: list[str]) -> None:
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False, encoding="utf-8-sig")


_init_csv(MEALS_CSV, ["timestamp", "date", "meal_slot", "items", "notes"])
_init_csv(WORKOUTS_CSV, ["timestamp", "date", "workout_type", "duration_min", "notes"])
_init_csv(WEIGHT_CSV, ["timestamp", "date", "weight_kg", "waist_cm", "sleep_h", "condition_1to5", "alcohol"])


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    return df


def append_row(path: str, row: dict) -> None:
    df = load_csv(path)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


st.set_page_config(page_title="감량 코치 트래커", layout="wide")
st.title("감량 코치 트래커 (로컬 저장 • CSV 누적)")

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
            append_row(
                WEIGHT_CSV,
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "date": d.isoformat(),
                    "weight_kg": weight,
                    "waist_cm": waist,
                    "sleep_h": sleep_h,
                    "condition_1to5": condition,
                    "alcohol": alcohol,
                },
            )
            st.success("저장 완료!")

    st.divider()
    st.subheader("2) 식단 기록 (카톡처럼 한 줄로 붙여넣기 가능)")
    meal_slot = st.selectbox("식사 구간", ["출근 전", "근무 중", "운동 전", "운동 후", "기타"])
    items = st.text_area("먹은 것(자유 입력)", placeholder="예) 위트빅스 3조각 + 프로틴 1스쿱, 햄 200g, 계란 3개")
    meal_notes = st.text_input("메모(선택)", placeholder="예) 저탄수일 / 술자리 / 외식")

    if st.button("식단 저장"):
        if items.strip() == "":
            st.error("먹은 것을 입력해줘.")
        else:
            append_row(
                MEALS_CSV,
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "date": d.isoformat(),
                    "meal_slot": meal_slot,
                    "items": items.strip(),
                    "notes": meal_notes.strip(),
                },
            )
            st.success("식단 저장 완료!")

    st.divider()
    st.subheader("3) 운동 기록")
    wtype = st.selectbox("운동 종류", ["상체", "하체", "전신", "유산소", "휴식"])
    duration = st.number_input("운동 시간(분)", min_value=0, step=5, value=60)
    wnotes = st.text_input("운동 메모(선택)", placeholder="예) 스쿼트 170, 데드 220 / 인터벌 10분")

    if st.button("운동 저장"):
        append_row(
            WORKOUTS_CSV,
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "date": d.isoformat(),
                "workout_type": wtype,
                "duration_min": duration,
                "notes": wnotes.strip(),
            },
        )
        st.success("운동 저장 완료!")


with tab2:
    st.subheader("📊 대시보드")
    wdf = load_csv(WEIGHT_CSV)
    mdf = load_csv(MEALS_CSV)
    odf = load_csv(WORKOUTS_CSV)

    # 정리
    if not wdf.empty:
        wdf["date"] = pd.to_datetime(wdf["date"])
        wdf = wdf.sort_values("date")

        # 7일 평균
        wdf["weight_kg"] = pd.to_numeric(wdf["weight_kg"], errors="coerce")
        wdf["waist_cm"] = pd.to_numeric(wdf["waist_cm"], errors="coerce")
        wdf["w7"] = wdf["weight_kg"].rolling(window=7, min_periods=1).mean()

        col1, col2, col3 = st.columns(3)
        latest = wdf.dropna(subset=["weight_kg"]).tail(1)
        if not latest.empty:
            col1.metric("최근 체중(kg)", f"{float(latest['weight_kg'].iloc[0]):.1f}")
            col2.metric("최근 7일 평균(kg)", f"{float(latest['w7'].iloc[0]):.1f}")
        if wdf["waist_cm"].dropna().shape[0] > 0:
            col3.metric("최근 허리(cm)", f"{float(wdf['waist_cm'].dropna().iloc[-1]):.1f}")

        st.write("")
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
    st.subheader("🗂 데이터 위치")
    st.code(DATA_DIR)

    st.write("아래 파일들이 누적 저장됩니다:")
    st.code("meals.csv\nworkouts.csv\nweight.csv")

    st.divider()
    st.subheader("⬇ CSV 다운로드(백업)")
    for label, path in [("meals.csv", MEALS_CSV), ("workouts.csv", WORKOUTS_CSV), ("weight.csv", WEIGHT_CSV)]:
        with open(path, "rb") as f:
            st.download_button(label=f"Download {label}", data=f, file_name=label, mime="text/csv")
