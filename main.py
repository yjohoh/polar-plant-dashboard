import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit + Plotly)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

# =========================
# 파일 유틸 함수 (NFC/NFD 대응)
# =========================
def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFC", name)

def find_file_by_normalized_name(directory: Path, target_name: str):
    target_nfc = normalize_name(target_name)
    for f in directory.iterdir():
        if normalize_name(f.name) == target_nfc:
            return f
    return None

# =========================
# 데이터 로딩
# =========================
@st.cache_data
def load_environment_data(data_dir: Path):
    data = {}
    for file in data_dir.iterdir():
        if file.suffix.lower() == ".csv":
            school = file.stem.replace("_환경데이터", "")
            data[school] = pd.read_csv(file)
    return data

@st.cache_data
def load_growth_data(xlsx_path: Path):
    xls = pd.ExcelFile(xlsx_path, engine="openpyxl")
    data = {}
    for sheet in xls.sheet_names:
        data[sheet] = xls.parse(sheet)
    return data

# =========================
# 데이터 로딩 실행
# =========================
DATA_DIR = Path("data")

with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data(DATA_DIR)
    growth_file = find_file_by_normalized_name(DATA_DIR, "4개교_생육결과데이터.xlsx")

    if growth_file is None:
        st.error("❌ 생육 결과 데이터 파일을 찾을 수 없습니다.")
        st.stop()

    growth_data = load_growth_data(growth_file)

# =========================
# 메타 정보
# =========================
EC_INFO = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0,
}

COLOR_MAP = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728",
}

ALL_SCHOOLS = list(EC_INFO.keys())

# =========================
# 사이드바
# =========================
st.sidebar.title("🏫 학교 선택")
selected_school = st.sidebar.selectbox(
    "학교",
    ["전체"] + ALL_SCHOOLS
)

# =========================
# 제목
# =========================
st.title("🌱 극지식물 최적 EC 농도 연구")

# =========================
# 탭 구성
# =========================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =====================================================
# TAB 1 : 실험 개요
# =====================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write("""
    본 연구는 극지식물의 생육에 영향을 미치는 **EC 농도**의 최적 조건을 도출하기 위해  
    서로 다른 EC 조건에서 재배된 학교별 실험 결과를 비교·분석하는 것을 목적으로 합니다.
    """)

    # EC 조건 표
    rows = []
    for school, ec in EC_INFO.items():
        rows.append({
            "학교명": school,
            "EC 목표": ec,
            "개체수": len(growth_data.get(school, [])),
            "색상": COLOR_MAP[school]
        })
    ec_df = pd.DataFrame(rows)
    st.dataframe(ec_df, use_container_width=True)

    # 주요 지표
    total_plants = sum(len(df) for df in growth_data.values())

    avg_temp = pd.concat(
        [df["temperature"] for df in env_data.values() if "temperature" in df]
    ).mean()

    avg_hum = pd.concat(
        [df["humidity"] for df in env_data.values() if "humidity" in df]
    ).mean()

    best_ec = 2.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_plants)
    c2.metric("평균 온도(°C)", f"{avg_temp:.1f}")
    c3.metric("평균 습도(%)", f"{avg_hum:.1f}")
    c4.metric("최적 EC", f"{best_ec} ⭐")

# =====================================================
# TAB 2 : 환경 데이터
# =====================================================
with tab2:
    st.subheader("학교별 환경 데이터 비교")

    avg_rows = []
    for school, df in env_data.items():
        avg_rows.append({
            "학교": school,
            "temperature": df["temperature"].mean(),
            "humidity": df["humidity"].mean(),
            "ph": df["ph"].mean(),
            "ec": df["ec"].mean(),
            "target_ec": EC_INFO.get(school)
        })
    avg_df = pd.DataFrame(avg_rows)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "평균 온도", "평균 습도",
            "평균 pH", "목표 EC vs 실측 EC"
        ]
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["temperature"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["humidity"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ph"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ec"], name="실측 EC", row=2, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["target_ec"], name="목표 EC", row=2, col=2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    # 시계열
    if selected_school != "전체" and selected_school in env_data:
        df = env_data[selected_school]

        fig_ts = make_subplots(rows=3, cols=1, shared_xaxes=True,
                               subplot_titles=["온도 변화", "습도 변화", "EC 변화"])

        fig_ts.add_scatter(x=df["time"], y=df["temperature"], row=1, col=1)
        fig_ts.add_scatter(x=df["time"], y=df["humidity"], row=2, col=1)
        fig_ts.add_scatter(x=df["time"], y=df["ec"], row=3, col=1)

        fig_ts.add_hline(
            y=EC_INFO[selected_school],
            row=3, col=1,
            line_dash="dash"
        )

        fig_ts.update_layout(height=700, font=PLOTLY_FONT)
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📂 환경 데이터 원본"):
        for school, df in env_data.items():
            st.write(f"### {school}")
            st.dataframe(df, use_container_width=True)

        csv_buffer = io.BytesIO()
        pd.concat(env_data.values()).to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        st.download_button(
            "CSV 다운로드",
            data=csv_buffer,
            file_name="환경데이터_통합.csv",
            mime="text/csv"
        )

# =====================================================
# TAB 3 : 생육 결과
# =====================================================
with tab3:
    st.subheader("EC별 생육 결과 분석")

    summary = []
    for school, df in growth_data.items():
        summary.append({
            "학교": school,
            "EC": EC_INFO.get(school),
            "평균 생중량": df["생중량(g)"].mean(),
            "평균 잎 수": df["잎 수(장)"].mean(),
            "평균 지상부 길이": df["지상부 길이(mm)"].mean(),
            "개체수": len(df)
        })

    sum_df = pd.DataFrame(summary)

    best_row = sum_df.loc[sum_df["평균 생중량"].idxmax()]
    st.metric("🥇 최고 평균 생중량 EC", f"{best_row['EC']} (하늘고 ⭐)")

    fig2 = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "평균 생중량", "평균 잎 수",
            "평균 지상부 길이", "개체수"
        ]
    )

    fig2.add_bar(x=sum_df["EC"], y=sum_df["평균 생중량"], row=1, col=1)
    fig2.add_bar(x=sum_df["EC"], y=sum_df["평균 잎 수"], row=1, col=2)
    fig2.add_bar(x=sum_df["EC"], y=sum_df["평균 지상부 길이"], row=2, col=1)
    fig2.add_bar(x=sum_df["EC"], y=sum_df["개체수"], row=2, col=2)

    fig2.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig2, use_container_width=True)

    all_growth = pd.concat(
        [df.assign(학교=school) for school, df in growth_data.items()]
    )

    fig_box = px.box(
        all_growth,
        x="학교",
        y="생중량(g)",
        color="학교"
    )
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    fig_sc1 = px.scatter(
        all_growth,
        x="잎 수(장)",
        y="생중량(g)",
        color="학교"
    )
    fig_sc1.update_layout(font=PLOTLY_FONT)

    fig_sc2 = px.scatter(
        all_growth,
        x="지상부 길이(mm)",
        y="생중량(g)",
        color="학교"
    )
    fig_sc2.update_layout(font=PLOTLY_FONT)

    st.plotly_chart(fig_sc1, use_container_width=True)
    st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("📂 생육 데이터 원본"):
        for school, df in growth_data.items():
            st.write(f"### {school}")
            st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        all_growth.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_통합.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
