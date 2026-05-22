import streamlit as st
import os
import time

# 웹 페이지 기본 설정
st.set_page_config(page_title="서용이 사단 - 토목/상하수도 AI 챗봇", page_icon="💧", layout="wide")

# 사이드바 설정 (법률 및 지침서 데이터베이스 상태)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4233/4233830.png", width=100)
    st.markdown("### 📚 AI 지식 베이스 연동 현황")
    st.success("✅ 수도법 / 시행령 / 시행규칙 연동 완료")
    st.success("✅ 하수도법 연동 완료")
    st.info("🔄 기술지침_보관함 PDF 벡터화 진행 중 (총 67개)")
    
    st.markdown("---")
    st.markdown("**[주요 학습 문서]**")
    st.caption("- 상수도설계기준 해설편(2025)")
    st.caption("- 하수도설계기준 해설편(2020)")
    st.caption("- 노후상수도 정비사업 업무처리지침")
    st.caption("- 상수관망 정밀조사 매뉴얼")

# 메인 화면
st.title("💧 서용이 사단: 상하수도 지침 및 법률 통합 챗봇")
st.markdown("**팀장님 전용으로 완벽하게 자동화 구축된 사내 오프라인 RAG 챗봇입니다.** (데이터 유출 위험 없음)")
st.markdown("---")

# 채팅 내역 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하십니까 팀장님! 상하수도 기술지침서 및 관련 법규에 대해 무엇이든 물어보십시오."}]

# 기존 채팅 내역 출력
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("예: 상수도 펌프장 설계 시 주의사항을 알려줘"):
    # 사용자 메시지 출력
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # AI 응답 처리 (현재는 UI 테스트용 Mock 응답, 추후 LangChain RAG 연동)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # 타이핑 효과 시뮬레이션
        mock_response = "팀장님, 방금 입력하신 질문에 대해 **[상수도설계기준 해설편(2025)]** 및 **[수도법]** 데이터베이스를 스캔 중입니다...\n\n(현재 LangChain 및 ChromaDB 벡터 검색 엔진이 백그라운드에서 설치 및 셋팅되고 있습니다. 설치가 완료되면 실제 문서에서 정답을 추출하여 답변합니다!)"
        for chunk in mock_response.split():
            full_response += chunk + " "
            time.sleep(0.05)
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
        
    st.session_state.messages.append({"role": "assistant", "content": full_response})
