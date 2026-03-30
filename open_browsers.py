import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
import time
import os
from threading import Thread

def open_profile(folder_name):
    # Đường dẫn chuẩn mà file Validator đang trỏ tới
    path = os.path.join(r"D:\ChromeAutomation\AdminScraperProfiles", folder_name)
    os.makedirs(path, exist_ok=True)
    print(f"🚀 Mở khoang đăng nhập cho: {folder_name}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=path,
                headless=False,
                viewport={"width": 1280, "height": 720},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://www.tiktok.com/login", timeout=60000)
            print(f"🟢 [{folder_name}] Đã tải xong trang Tiktok. Mời Sếp Đăng nhập!")
            time.sleep(9999999)  # Treo vĩnh viễn chờ Sếp tắt
    except Exception as e:
        print(f"❌ Lỗi khi mở {folder_name}: {e}")

print("=========================================")
print("   BTOOL: MỞ 2 TRÌNH DUYỆT CÙNG LÚC      ")
print("=========================================")

t1 = Thread(target=open_profile, args=("Profile_Scraper_1",))
t2 = Thread(target=open_profile, args=("Profile_Scraper_2",))

t1.start()
time.sleep(2) # Hé mở dần để cửa sổ khỏi đè 1 mớ
t2.start()

t1.join()
t2.join()
