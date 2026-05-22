import streamlit as st
import pickle
from pathlib import Path
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
from core.aggregator import summarize

st.set_page_config(page_title="지도 대시보드", layout="wide")

if not st.session_state.get("authentication_status"):
    st.warning("먼저 로그인 해주세요.")
    st.stop()

st.title("🗺️ 지도 대시보드")

# 프로젝트 선택
data_dir = Path("data")
projects = [p.name for p in data_dir.iterdir() if p.is_dir()] if data_dir.exists() else []
if not projects:
    st.info("업로드된 현장이 없습니다. 먼저 데이터 업로드를 진행하세요.")
    st.stop()

default_idx = (
    projects.index(st.session_state.get("current_project"))
    if st.session_state.get("current_project") in projects
    else 0
)
project = st.selectbox("현장 선택", projects, index=default_idx)

cache_path = data_dir / project / "processed.pkl"
if not cache_path.exists():
    st.error("처리된 데이터가 없습니다. 다시 업로드하세요.")
    st.stop()

with open(cache_path, "rb") as f:
    gdf_dict = pickle.load(f)

layer_name = st.selectbox("레이어 선택", list(gdf_dict.keys()))
gdf = gdf_dict[layer_name]

# ─── 통계 카드 ───
stats = summarize(gdf)
if "error" in stats:
    st.warning(stats["error"])
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 관로 수", f"{stats.get('총_관로수', 0):,}")
    c2.metric("총 연장 (km)", f"{stats.get('총_연장_km', 0):,}")
    c3.metric("노후관 30년+ (m)", f"{stats.get('노후관_30년이상_연장_m', 0):,}")
    c4.metric("노후관 비율 (%)", f"{stats.get('노후관_비율_%', 0)}")

# ─── 지도 ───
st.subheader("관로 지도")
center = [gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()]
m = folium.Map(location=center, zoom_start=14, tiles="CartoDB positron")

# 관종별 색상
color_map = {
    "도수관": "#1f77b4", "송수관": "#2ca02c", "배수관": "#ff7f0e",
    "급수관": "#d62728", "기타": "#7f7f7f",
}

def style_fn(feature):
    nm = feature["properties"].get("FTR_CDE_NM", "기타")
    return {"color": color_map.get(nm, "#7f7f7f"), "weight": 3}

# 너무 많으면 샘플링
display_gdf = gdf if len(gdf) <= 5000 else gdf.sample(5000, random_state=0)

folium.GeoJson(
    display_gdf.to_json(),
    style_function=style_fn,
    tooltip=folium.GeoJsonTooltip(
        fields=[c for c in ["FTR_CDE_NM", "SAA_CDE", "MOP_CDE_NM", "BYC_LEN", "IST_YMD"]
                if c in display_gdf.columns],
        aliases=["관종", "구경(mm)", "재질", "연장(m)", "설치일"],
    ),
).add_to(m)

st_folium(m, width=None, height=600, returned_objects=[])

# ─── 차트 ───
col1, col2 = st.columns(2)

with col1:
    if stats.get("관종별_연장"):
        df_t = pd.DataFrame(stats["관종별_연장"].items(), columns=["관종", "연장(m)"])
        fig = px.pie(df_t, names="관종", values="연장(m)", title="관종별 연장")
        st.plotly_chart(fig, use_container_width=True)

    if stats.get("재질별_연장"):
        df_m = pd.DataFrame(stats["재질별_연장"].items(), columns=["재질", "연장(m)"])
        fig = px.bar(df_m, x="재질", y="연장(m)", title="재질별 연장")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if stats.get("구경별_연장"):
        df_d = pd.DataFrame(stats["구경별_연장"].items(), columns=["구경(mm)", "연장(m)"])
        fig = px.bar(df_d, x="구경(mm)", y="연장(m)", title="구경별 연장")
        st.plotly_chart(fig, use_container_width=True)

    if stats.get("매설년대별_연장"):
        df_y = pd.DataFrame(stats["매설년대별_연장"].items(), columns=["년대", "연장(m)"])
        fig = px.bar(df_y, x="년대", y="연장(m)", title="매설년대별 연장")
        st.plotly_chart(fig, use_container_width=True)

# ─── 원본 속성 ───
with st.expander("속성 테이블 보기"):
    st.dataframe(gdf.drop(columns="geometry").head(100))
