import streamlit as st
import streamlit_authenticator as stauth
import yaml
from pathlib import Path

st.set_page_config(page_title="상수도 GIS 대시보드", layout="wide", page_icon="💧")

# 로그인
with open("config/users.yaml", "r", encoding="utf-8") as f:
    auth_config = yaml.safe_load(f)

authenticator = stauth.Authenticate(
    auth_config["credentials"],
    auth_config["cookie"]["name"],
    auth_config["cookie"]["key"],
    auth_config["cookie"]["expiry_days"],
)

authenticator.login(location="main")

if st.session_state.get("authentication_status"):
    authenticator.logout(location="sidebar")
    st.sidebar.success(f"{st.session_state['name']} 님 환영합니다")

    st.title("💧 상수도 GIS 대시보드")
    st.markdown(
        """
        ### 사용 방법
        1. 왼쪽 메뉴에서 **데이터 업로드** 선택
        2. 현장명 입력 후 shp 파일 세트(.shp, .shx, .dbf, .prj)를 **ZIP으로 압축해 업로드**
        3. **지도 대시보드**에서 시각화와 통계 확인
        
        ### 지원 좌표계
        - 입력: EPSG:5186 (중부원점) — `.prj` 없으면 자동 적용
        - 표시: EPSG:4326 (WGS84)
        
        ### 표준 스키마
        국토교통부 지하시설물 전산화 표준(UFID) 상수도 관로 스키마를 따릅니다.
        """
    )

    # 데이터 폴더 생성
    Path("data").mkdir(exist_ok=True)

elif st.session_state.get("authentication_status") is False:
    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
elif st.session_state.get("authentication_status") is None:
    st.warning("로그인 해주세요.")
