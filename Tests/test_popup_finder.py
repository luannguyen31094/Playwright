import time
import os
import sys
import json
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Core import db_manager

print("Dang nap thong tin Worker_01 tu Database...")
try:
    folder, proj, status, email, password, acc_status = db_manager.get_worker_full_config("Worker_01")
except Exception as e:
    print("Loi Database:", e)
    sys.exit()

PROFILE = folder or f"Profile_Test_{int(time.time())}"
PROJECT_ID = proj or "5e85dc56-0ad8-418c-88f6-b26573af489f"
BASE_URL = f"https://labs.google/fx/vi/tools/flow/project/{PROJECT_ID}"
USER_DATA_DIR = r"D:\ChromeAutomation"

with sync_playwright() as p:
    user_data_path = os.path.join(USER_DATA_DIR, PROFILE)
    print(f"Mo Profile: {user_data_path}")
    browser_context = p.chromium.launch_persistent_context(
        user_data_path,
        headless=True,
        viewport={'width': 1280, 'height': 800},
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    
    page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
    page.set_default_timeout(60000)
    
    print(f"Dang truy cap: {BASE_URL}")
    page.goto(BASE_URL, wait_until="networkidle")

    print("Cho giao dien tai...")
    time.sleep(10) # Chờ an toàn cho React render

    print("Chup anh man hinh luu vao: flow_screenshot.png")
    page.screenshot(path="flow_screenshot.png", full_page=True)

    print("Quet tat ca cac Nut (Buttons) tren man hinh...")
    buttons_info = page.evaluate("""
        () => {
            const btns = Array.from(document.querySelectorAll('button, [role="button"], [role="menuitem"]'));
            return btns.map(b => ({
                text: b.innerText.trim(),
                ariaLabel: b.getAttribute('aria-label') || "",
                ariaHasPopup: b.getAttribute('aria-haspopup') || "",
                className: b.className,
                html: b.outerHTML.substring(0, 150).replace(/[\\n\\r]+/g, ' ')
            })).filter(b => b.text || b.ariaLabel || b.html.includes('svg'));
        }
    """)

    with open("buttons_dump.json", "w", encoding="utf-8") as f:
        json.dump(buttons_info, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Đã tìm thấy {len(buttons_info)} nút! Lưu vào buttons_dump.json")
    browser_context.close()
