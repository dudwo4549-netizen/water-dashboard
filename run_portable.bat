@echo off
chcp 65001 > nul
title 💧 상수도 공정관리 & 목표유수율 통합 대시보드 기동기

echo ====================================================================
echo   💧 상수도 통합 성과관리 및 AI 기술자문 시스템 (서용이 사단 제작)
echo ====================================================================
echo.
echo   * 본 시스템은 로컬 환경에서 구동되는 Flask 서버와 웹 프론트엔드입니다.
echo   * 엑셀 연동 및 RAG 기술자문 AI 챗봇 구동을 시작합니다.
echo.

:: 1. Python 환경 체크
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 시스템에 Python이 설치되어 있지 않거나 환경 변수(PATH)에 등록되어 있지 않습니다.
    echo         https://www.python.org 에서 Python 3.8 이상을 설치한 후 다시 시도해주십시오.
    echo.
    pause
    exit /b
)

:: 2. 필수 라이브러리 설치
echo [STEP 1] 필수 라이브러리 검사 및 설치 중 (requirements.txt)...
echo          (첫 실행 시 또는 패키지 누락 시 시간이 다소 소요될 수 있습니다.)
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] 일부 패키지 설치 중 경고나 오류가 발생했습니다.
    echo           설치 상태를 수동으로 점검해주십시오.
)
echo.

:: 3. 브라우저 자동 기동 예약 (서버가 열릴 시간을 벌기 위해 3초 대기 후 오픈)
echo [STEP 2] 대시보드 웹 브라우저를 실행합니다...
start "" "http://127.0.0.1:5000"

:: 4. Flask 백엔드 가동
echo [STEP 3] 로컬 플라스크 백엔드 서버를 기동합니다.
echo          * 서버를 종료하려면 이 창을 닫거나 Ctrl+C를 누르십시오.
echo ====================================================================
echo.
python app.py

pause
