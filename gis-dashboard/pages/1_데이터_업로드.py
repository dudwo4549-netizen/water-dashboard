import streamlit as st
from pathlib import Path
import pickle
from core.shp_loader import load_zip_to_gdf
from core.code_mapper import apply_code_mapping

st.set_page_config(page_title="데이터 업로드", layout="wide")

if not st.session_state.get("authentication_status"):
    st.warning("먼저 로그인 해주세요.")
    st.stop()

st.title("📤 데이터 업로드")

project_name = st.text_input("현장(지역)명", placeholder="예: 강남구_상수도_2024")
uploaded = st.file_uploader(
    "shp 세트를 ZIP으로 압축해 업로드 (.shp, .shx, .dbf, .prj 포함)",
    type=["zip"],
)

if uploaded and project_name:
    project_dir = Path("data") / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    with st.spinner("파일 처리 중..."):
        gdf_dict = load_zip_to_gdf(uploaded, project_dir / "raw")

    if not gdf_dict:
        st.error("ZIP 안에서 shp 파일을 찾지 못했습니다.")
        st.stop()

    st.success(f"{len(gdf_dict)}개 shp 로드 완료")

    processed = {}
    for name, gdf in gdf_dict.items():
        st.subheader(f"📄 {name}")
        st.write(f"- 피처 수: **{len(gdf):,}**")
        st.write(f"- 지오메트리 타입: {gdf.geom_type.unique().tolist()}")
        st.write(f"- 컬럼: {list(gdf.columns)}")

        gdf_mapped = gdf.copy()
        # 속성 부분만 코드 매핑
        attrs = apply_code_mapping(gdf.drop(columns="geometry"))
        for col in attrs.columns:
            gdf_mapped[col] = attrs[col].values

        st.dataframe(gdf_mapped.drop(columns="geometry").head(5))
        processed[name] = gdf_mapped

    # 세션 + 디스크 저장 (대시보드 페이지에서 사용)
    cache_path = project_dir / "processed.pkl"
    with open(cache_path, "wb") as f:
        pickle.dump(processed, f)

    st.session_state["current_project"] = project_name
    st.success(f"✅ '{project_name}' 저장 완료. 이제 **지도 대시보드** 페이지로 이동하세요.")
