@echo off
:: 1. SỬA LỖI FONT: Ép CMD dùng bảng mã UTF-8
chcp 65001 >nul
title GOOGLE LABS SAAS SYSTEM - V8.2 (DATABASE DRIVEN)

echo ======================================================
echo     DANG KHOI DONG HE THONG SAAS V8.2 - LUAN ULTRA
echo      (Quan ly Profile và Project qua PostgreSQL)
echo ======================================================

:: 2. Chuyển vào thư mục dự án
cd /d "C:\Users\Admin\DockerFL\n8n-selenium-bridge"

:: 3. SỬA LỖI CODE: Thiết lập đường dẫn gốc cho Python
set PYTHONPATH=%CD%

:: Mở Gateway ở một cửa sổ riêng biệt
echo [%time%] 🌐 Dang mo Gateway tren cua so moi...
start "GATEWAY 8000" cmd /c "START_GATEWAY.bat"

:: 4. Chạy hệ thống quản lý tập trung (Thay thế cho việc mở nhiều cửa sổ)
echo [%time%] 🚀 Dang ban giao quyen dieu khien cho System Manager...
set PYTHONIOENCODING=utf-8
python system_manager.py

pause