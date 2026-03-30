import time
import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Core import db_manager
from playwright.sync_api import sync_playwright
from Core.js_payloads import get_morphing_js

print("🔎 Đang nạp thông tin Worker_01 từ Database...")
try:
    folder, proj, status, email, password, acc_status = db_manager.get_worker_full_config("Worker_01")
except:
    sys.exit()

PROFILE = folder or f"Profile_Test_{int(time.time())}"
PROJECT_ID = proj or "5e85dc56-0ad8-418c-88f6-b26573af489f"
BASE_URL = f"https://labs.google/fx/vi/tools/flow/project/{PROJECT_ID}"
USER_DATA_DIR = r"D:\ChromeAutomation"

def handle_login(pg, em, pw):
    print("🔑 Đang kiểm tra đăng nhập...")
    try:
        email_box = pg.locator('input[type="email"]')
        if email_box.is_visible(timeout=2000):
            email_box.fill(em)
            pg.locator("button:has-text('Tiếp theo'), button:has-text('Next')").click()
            pg.wait_for_timeout(4000)
            
        pass_box = pg.locator('input[type="password"]')
        if pass_box.is_visible(timeout=5000):
            pass_box.first.click()
            pg.keyboard.type(pw, delay=50)
            pg.wait_for_timeout(1000)
            pg.locator("button:has-text('Tiếp theo'), button:has-text('Next')").first.click()
            pg.wait_for_timeout(5000)
    except Exception as e:
        pass

with sync_playwright() as p:
    user_data_path = os.path.join(USER_DATA_DIR, PROFILE)
    browser_context = p.chromium.launch_persistent_context(
        user_data_path,
        headless=False,
        viewport={'width': 1280, 'height': 800},
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    
    page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
    page.set_default_timeout(60000)
    page.goto(BASE_URL, wait_until="commit")

    for i in range(30):
        create_btn = page.locator("button:has-text('Create with Flow')").first
        if create_btn.is_visible(timeout=500):
            create_btn.click()
            page.wait_for_timeout(3000)
            continue
            
        if "accounts.google.com" in page.url or page.locator('input[type="email"]').is_visible(timeout=500):
            handle_login(page, email, password)
        elif "project.getProject" in page.url or page.locator('div[role="textbox"]').is_visible(timeout=500):
            print("🎉 Đã vào Flow!")
            break
        else:
            time.sleep(2)

    # DUMP DOM CỦA PHẦN NHẬP TEXT ĐỂ TÌM NÚT SUBMIT
    time.sleep(3)
    try:
        html_content = page.content()
        with open(r"C:\tmp\flow_dom.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("💾 Đã lưu DOM vào C:\\tmp\\flow_dom.html")
    except Exception as e:
        print("Lỗi lưu DOM:", e)

    print("\n--- BẮT ĐẦU TEST UPLOAD GỬI TỪ N8N ---")
    mock_upload_payload = {
        "imageInput": {
            "rawImageBytes": "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=",
            "mimeType": "image/jpeg",
            "isUserUploaded": True,
            "aspectRatio": "IMAGE_ASPECT_RATIO_PORTRAIT"
        },
        "clientContext": {
            "sessionId": ";" + str(int(time.time())),
            "tool": "ASSET_MANAGER"
        }
    }
    
    script = get_morphing_js("upload", "v1:uploadUserImage", mock_upload_payload, PROJECT_ID)
    evaluate_script = f"""
    async () => {{
        return await new Promise((resolve) => {{
            const arguments = [resolve];
            {script}
        }});
    }}
    """
    
    page.on("console", lambda msg: print(f"🖥️ [Browser]: {msg.text}"))
    page.on("request", lambda req: print(f"🌐 [Network] {req.url}") if ("batch" in req.url or "predict" in req.url or "flow" in req.url) else None)
    
    print("🔥 Using Playwright Native Fill...")
    try:
        page.locator('div[role="textbox"], textarea').first.click()
        page.keyboard.type(f"Up-{int(time.time())}")
    except Exception as e:
        print("Could not fill:", e)
        
    print("🔥 Injecting Upload JS to Click & Intercept...")
    try:
        # Tắt logic tự click trong JS, Playwright sẽ bấm
        # Hoặc kệ JS click, nó đằng nào cũng click
        result = page.evaluate(evaluate_script)
        print("✅ JS Executed successfully! Kết quả trả về:", result)
    except Exception as e:
        print("❌ JS LỖI:", e)
    
    time.sleep(30)
    browser_context.close()
