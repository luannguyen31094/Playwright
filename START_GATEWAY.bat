@echo off
:: 1. SỬA LỖI FONT: Ép CMD dùng bảng mã UTF-8
chcp 65001 >nul
title GATEWAY 8000 (HTTP API TRUNTER)

echo ======================================================
echo     GATEWAY API SERVER - CONG 8000
echo ======================================================

:: 2. Chuyển vào thư mục dự án
cd /d "C:\Users\Admin\DockerFL\n8n-selenium-bridge"

:: 3. Thiết lập đường dẫn gốc cho Python
set PYTHONPATH=%CD%
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

:: 4. Chạy Gateway thẳng trên CMD này
python gateway.py

pause
