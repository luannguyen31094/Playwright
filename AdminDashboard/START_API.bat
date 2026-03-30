@echo off
cd /d "%~dp0"
echo [1/2] Dang kiem tra va cai dat thu vien Python (Flask)...
pip install flask flask-cors psycopg2 pyngrok
echo.
echo [2/2] Kich hoat Dong co API (Thu muc hien tai: %CD%)...
echo ===================================================
python backend_api.py
pause
