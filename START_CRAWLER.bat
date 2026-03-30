@echo off
chcp 65001 >nul
title GOOGLE LABS - TIKTOK DAILY CRAWLER

echo ======================================================
echo          TIKTOK SHOP - TWO-STAGE SCRAPER
echo             (Chay thu cong lay du lieu)
echo ======================================================

cd /d "C:\Users\Admin\DockerFL\n8n-selenium-bridge"
set PYTHONPATH=%CD%

echo.
echo [1] Dang chay GIAI DOAN 1: Thu thap link tai tung Category (ADMIN PROFILE)
echo.
set CATEGORY_URL=https://www.tiktok.com/shop/vn/category/menswear-underwear-824328
set WEBHOOK_URL=https://thorough-macaw-thankfully.ngrok-free.app/webhook-test/n8n-callback
python Tools/TiktokScraper/category_scraper_admin.py


echo [DONE] Hoan thanh quet chien dich!
pause
