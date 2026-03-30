import time
import os
import sys

# Đảm bảo import được thư mục Core
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Core import db_manager
from playwright.sync_api import sync_playwright
from Core.js_payloads import get_morphing_js

print("🔎 Đang nạp thông tin Worker_01 từ Database...")
try:
    folder, proj, status, email, password, acc_status = db_manager.get_worker_full_config("Worker_01")
except Exception as e:
    print("❌ Lỗi Database:", e)
    sys.exit()

if not email or not password:
    print("❌ LỖI: Worker_01 chưa có Email và Password trong Database!")
    print("👉 Hãy cấu hình lại Worker_01 (Tài khoản Google) / Status: ON rồi chạy lại Script này để Test!")
    input("Nhấn Enter để thoát...")
    sys.exit()

PROFILE = folder or f"Profile_Test_{int(time.time())}"
PROJECT_ID = proj or "5e85dc56-0ad8-418c-88f6-b26573af489f"
BASE_URL = f"https://labs.google/fx/vi/tools/flow/project/{PROJECT_ID}"
USER_DATA_DIR = r"D:\ChromeAutomation"

print("✅ Đã tìm thấy Email:", email)
print("🚀 Đang khởi động Playwright với giao diện (Headless=False)...")

def handle_login(pg, em, pw):
    print("🔑 Đang tiến hành đăng nhập Google...")
    try:
        email_box = pg.locator('input[type="email"]').first
        if email_box.is_visible(timeout=5000):
            email_box.fill(em)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(4000)
            
        pass_box = pg.locator('input[type="password"][name="Passwd"], input[type="password"]').first
        if pass_box.is_visible(timeout=10000):
            pass_box.click()
            pg.keyboard.type(pw, delay=50)
            pg.wait_for_timeout(1000)
            pg.keyboard.press("Enter")
            print("✅ Đã nhập Password. Chờ Google xử lý (có thể hiện Captcha)...")
            pg.wait_for_timeout(10000)
            return True
        return False
    except Exception as e:
        print("❌ Lỗi trong quá trình đăng nhập:", str(e))
        return False

with sync_playwright() as p:
    user_data_path = os.path.join(USER_DATA_DIR, PROFILE)
    browser_context = p.chromium.launch_persistent_context(
        user_data_path,
        headless=False,
        viewport={'width': 1280, 'height': 800},
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ],
        ignore_default_args=["--enable-automation"]
    )
    
    page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
    page.set_default_timeout(60000)
    
    print(f"🌐 Đang truy cập: {BASE_URL}")
    page.goto(BASE_URL, wait_until="commit")

    # Kiểm tra login
    for i in range(30):
        create_btn = page.locator("button:has-text('Create with Flow')").first
        if create_btn.is_visible(timeout=500):
            print("👆 Phát hiện màn hình chờ, đang bấm 'Create with Flow'...")
            create_btn.click()
            page.wait_for_timeout(3000)
            continue
            
        if "accounts.google.com" in page.url or page.locator('input[type="email"]').is_visible(timeout=500):
            handle_login(page, email, password)
        elif page.locator('div[role="textbox"][data-slate-editor="true"], textarea').first.is_visible(timeout=500):
            print("🎉 Đã vượt qua Login và vào giao diện Flow thành công!")
            break
        else:
            print("Đang chờ tải trang hoặc Captcha...")
            time.sleep(2)

    print("\n--- BẮT ĐẦU TEST BƠM JAVASCRIPT PAYLOAD ---")
    mock_payload = {
        "prompt": "Test AI generated image UI logic",
        "ratio": "916",
        "outputs": 1,
        "ref_ids": ["dummy-uuid-1"]
    }
    
    script = get_morphing_js("image_gen", "v1:something", mock_payload, PROJECT_ID)
    evaluate_script = f"""
    async () => {{
        return await new Promise((resolve) => {{
            const arguments = [resolve];
            {script}
        }});
    }}
    """
    
    print("🔥 Injecting JS...")
    try:
        page.evaluate(evaluate_script)
        print("✅ JS Executed successfully! Vui lòng quan sát trình duyệt xem chuột có tự bấm và gõ đúng không nhé!")
    except Exception as e:
        print("❌ JS LỖI:", e)
    
    print("⏳ Giữ trình duyệt mở thêm 60s để Sếp xem kết quả nha...")
    time.sleep(60)
    browser_context.close()
