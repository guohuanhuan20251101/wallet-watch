@echo off
call .venv\Scripts\activate.bat
start http://localhost:8501
streamlit run main.py
pause
