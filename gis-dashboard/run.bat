@echo off
cd /d "%~dp0"
echo 가상환경을 활성화하고 대시보드를 실행합니다...
call .venv\Scripts\activate.bat
streamlit run app.py
pause
