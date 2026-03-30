import os
import sys
import time
import json
import traceback
import re
import urllib.parse
from bs4 import BeautifulSoup
import requests
import requests
from playwright.sync_api import sync_playwright

# Setup paths to import Core
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

from Core.db_manager import get_worker_full_config
from Core.database_info import get_sys_var
from Core.human_logic import PlaywrightCaptchaSolver
import Tools.TiktokScraper.tiktok_db as tiktok_db

def now(): return time.strftime('%H:%M:%S')

USER_DATA_DIR_BASE = get_sys_var('ROOT_PATH', r'D:\ChromeAutomation')
SHOWCASE_URL = "https://shop.tiktok.com/streamer/showcase/product/list"
SHOWCASE_API = "api/v1/streamer_desktop/showcase_product/list"
SEARCH_API = "api/v1/streamer_desktop/products" # Need to determine the actual API endpoint for product searching by URL

class WebAffiliateValidator:
    def __init__(self, browser_profile_path):
        self.profile_path = browser_profile_path
        self.playwright = None
        self.browser = None
        self.page = None
        
        self.showcase_products = []
        self.collected_showcase_products = []
        self.checking_product_id = None
        self.last_commission_data = None
        self.needs_login = False
        self.is_test_login = False

    def start_context(self):
        """Khởi tạo Chromium với Profile sẵn có của hệ thống"""
        print(f"[{now()}] 🚀 Mở trình duyệt sử dụng Profile: {self.profile_path}")
        self.playwright = sync_playwright().start()
        
        if getattr(self, "is_test_login", False):
            print(f"[{now()}] 🧪 Mở trình duyệt ở chế độ TEST LOGIN (Ẩn danh / Không dùng Profile cũ)")
            self.browser = self.playwright.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                ]
            )
            context = self.browser.new_context(
                timezone_id="Asia/Ho_Chi_Minh",
                locale="vi-VN",
                viewport={'width': 1280, 'height': 720}
            )
            self.page = context.new_page()
            self.page.on("response", self.handle_api_response)
            return

        self.browser = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_path,
            headless=False,
            timezone_id="Asia/Ho_Chi_Minh",
            locale="vi-VN",
            viewport={'width': 1280, 'height': 720},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ]
        )
        
        pages = self.browser.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = self.browser.new_page()
            
        self.page.on("response", self.handle_api_response)

    def close_context(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print(f"[{now()}] 🧹 Đã đóng trình duyệt.")

    def handle_api_response(self, response):
        """Lắng nghe và bóc tách dữ liệu từ API TikTok"""
        try:
            url = response.url
            
            # Log các API liên quan đến Đăng nhập để Debug "Max attempts"
            if "passport/web/" in url or "login/" in url:
                try:
                    if response.request.method == "POST":
                        raw = response.body().decode('utf-8')
                        print(f"[{now()}] 🕵️ [NETWORK LOGIN] {url.split('?')[0]} -> {raw[:300]}")
                except Exception:
                    pass
            
            if SHOWCASE_API in url and response.status == 200:
                raw_body = response.body()
                body = json.loads(raw_body.decode('utf-8'))
                
                if body.get("code") == 98001002:
                    print(f"[{now()}] ⏭️ [INTERCEPT] Gói tin báo chưa đăng nhập (Code 98001002). Sẽ yêu cầu đăng nhập...")
                    self.needs_login = True
                elif "data" not in body:
                    print(f"[{now()}] ⏭️ [INTERCEPT] Bỏ qua gói tin Showcase rác (Không có data).")
                else:
                    print(f"[{now()}] 📡 [INTERCEPT] Bắt và giải phẫu gói tin API Showcase List từ Tiktok!")
                    products = body["data"].get("products", [])
                    print(f"[{now()}] 👉 Phát hiện {len(products)} sản phẩm trong gói tin này.")
                    if products:
                        self.collected_showcase_products.extend(products)
            
            if "product_link/check" in url and response.status == 200:
                raw_body = response.body()
                data = json.loads(raw_body.decode('utf-8'))
                print(f"[{now()}] 📡 [INTERCEPT] Bắt được dữ liệu TÌM KIẾM SẢN PHẨM!")
                self.last_commission_data = data
                
        except Exception as e:
            err_str = str(e).lower()
            if "getresponsebody" not in err_str and "closed" not in err_str:
                 print(f"[{now()}] ❌ Lỗi Intercept: {e}")

    def solve_captcha_inline(self):
        """Giải Captcha (Slide/Rotate/2 Hình) Inline"""
        print(f"[{now()}] ⚠️ [BỐT GIẢI MÃ] Bắt đầu quy trình giải Captcha...")
        solver_instance = PlaywrightCaptchaSolver(self.page)
        captcha_context = {
            'module_name': 'Affiliate_Web_Validator',
            'worker_id': os.environ.get("WORKER_ID", "adminLuan031094")
        }
        
        captcha_cleared = False
        for attempt in range(1, 6):
            print(f"[{now()}] 🤖 [BỐT GIẢI MÃ] Lần chọt {attempt}/5...")
            solver_instance.solve(captcha_context)
            time.sleep(3)
            
            captcha_loc_inner = self.page.locator(".captcha-verify-container, #captcha-verify-image")
            if captcha_loc_inner.count() == 0 or not captcha_loc_inner.first.is_visible():
                captcha_cleared = True
                print(f"[{now()}] 🎉 [BỐT GIẢI MÃ] THÀNH CÔNG ở lần thử {attempt}!")
                break
                
            time.sleep(2)
        
        if not captcha_cleared:
            print(f"[{now()}] ⏳ [BỐT GIẢI MÃ] Thất bại toàn tập sau 5 lần. Cần can thiệp tay!")
            webhook_url = os.environ.get("WEBHOOK_URL")
            if webhook_url:
                try:
                    payload = {
                        "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                        "task_code": "STEP_1_CAPTCHA_FAILED",
                        "status": "failed",
                        "data": {"worker_id": captcha_context.get('worker_id')},
                        "message": "Giải Captcha thất bại, vui lòng vào Chrome Remote can thiệp tay."
                    }
                    r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                    print(f"[{now()}] 📲 Đã bắn Webhook gọi N8N báo Cứu Viện Captcha! (HTTP {r.status_code})")
                except Exception as e:
                    print(f"[{now()}] ❌ Lỗi bắn Webhook báo Captcha Failed: {e}")
                    
            for _ in range(300):
                captcha_loc_inner2 = self.page.locator(".captcha-verify-container, #captcha-verify-image")
                if captcha_loc_inner2.count() == 0 or not captcha_loc_inner2.first.is_visible():
                    break
                time.sleep(1)
        
        print(f"[{now()}] ✅ Cổng Captcha đã mở!")
        time.sleep(3)

    def ensure_logged_in_and_no_captcha(self):
        """Kiểm tra xem trang có bị đá văng ra Login hay không, và đợi giải Captcha nếu có"""
        # Đợi 3s để trang kịp redirect nếu chưa đăng nhập
        time.sleep(3)
        curr_url = self.page.url.lower()
        
        # 1. Đợi đăng nhập thủ công nếu bị văng ra trang Login / Passport
        current_username = None
        email_clicked = False # Tránh bấm gửi email / otp nhiều lần
        webhook_sent = False
        login_retry_count = 0 # Đếm số lần bị Tiktok chửi "Truy cập thường xuyên"
        
        if "login" in curr_url or "passport" in curr_url or self.needs_login:
            print(f"[{now()}] 🛑 PHÁT HIỆN CHƯA ĐĂNG NHẬP!")
            print(f"[{now()}] � Đang thử lấy tài khoản từ CSDL để Auto-Login...")
            account = tiktok_db.get_tiktok_account()
            
            if account and account.get('username') and account.get('password'):
                username = account['username']
                password = account['password']
                print(f"[{now()}] 🤖 Bắt đầu Auto-Login với tài khoản: {username}")
                
                try:
                    # Truy cập thẳng vào ô điền user (Tiktok gộp chung Tên người dùng và Số điện thoại ở layout mới tùy giao diện)
                    user_input = self.page.locator("input[name='username'], input[type='text'], input[placeholder*='Email'], input[placeholder*='Phone']").first
                    if user_input.count() > 0:
                        user_input.fill(username)
                        time.sleep(0.5)
                        
                    pass_input = self.page.locator("input[type='password']").first
                    if pass_input.count() > 0:
                        pass_input.fill(password)
                        time.sleep(0.5)
                        
                    login_btn = self.page.locator("button[type='submit'], button[data-e2e='login-button']").first
                    if login_btn.count() > 0:
                        login_btn.click()
                        print(f"[{now()}] 🖱️ Đã nhấn nút Đăng nhập. Chờ kết quả hoặc Captcha...")
                        time.sleep(5)
                except Exception as e:
                    print(f"[{now()}] ❌ Lỗi quá trình Auto-Login: {e}")
            else:
                print(f"[{now()}] ⚠️ Không có tài khoản Auto-Login trong CSDL. Chuyển sang chờ người dùng đăng nhập tay.")
                print(f"[{now()}] �👉 VUI LÒNG MỞ TRÌNH DUYỆT VÀ ĐĂNG NHẬP VÀO TIKTOK CREATOR CENTER (Bằng QR Code hoặc Phone).")
                print(f"[{now()}] ⏳ Hệ thống sẽ tạm dừng tại đây cho đến khi bạn đăng nhập thành công...")
            
            loop_count = 0
            while "login" in self.page.url.lower() or "passport" in self.page.url.lower():
                loop_count += 1
                if loop_count % 5 == 0:
                    print(f"[{now()}] 🔄 [DEBUG] Vẫn đang ở trang Login. Đang quét tìm Captcha/OTP... URL: {self.page.url}")
                    try:
                        self.page.screenshot(path="debug_login_hang.png")
                    except Exception:
                        pass
                
                # 1. Check Captcha Xoay / Kéo / 3D (Ưu tiên số 1, chặn không cho click tiếp)
                captcha_locator = self.page.locator(".captcha-verify-container, #captcha-verify-image")
                if captcha_locator.count() > 0 and captcha_locator.first.is_visible():
                    print(f"[{now()}] ⚠️ Phát hiện Captcha overlay! Tiến hành gọi Tool giải mã...")
                    self.solve_captcha_inline()
                    # If captcha is for email verification, send a specific webhook
                    if email_clicked:
                        webhook_url = os.environ.get("WEBHOOK_URL")
                        if webhook_url:
                            try:
                                payload = {
                                    "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                                    "task_code": "EMAIL_CAPTCHA",
                                    "status": "captcha_required",
                                    "data": {"email": current_username}, # Assuming current_username is email here
                                    "message": "Tiktok chặn luồng Email bằng Captcha. Sếp vào xử lý bằng tay nhé!"
                                }
                                r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                                print(f"[{now()}] 📲 Đã bắn Webhook báo EMAIL CAPTCHA! (HTTP {r.status_code})")
                            except Exception as e:
                                print(f"[{now()}] ❌ Lỗi bắn Webhook báo Email Captcha: {e}")
                    continue
                
                # 2. Cảnh báo limit và thử lại (Dò tìm thẻ lỗi thay vì tìm chữ vì đa ngôn ngữ)
                max_attempts_locator = self.page.locator("div[type='error'] span[role='status']")
                if max_attempts_locator.count() > 0 and max_attempts_locator.first.is_visible():
                    error_text = max_attempts_locator.first.inner_text()
                    print(f"[{now()}] 💀 TIKTOK BÁO LỖI: '{error_text}'. Đã thử {login_retry_count}/3 lần.")
                    
                    if login_retry_count >= 3:
                        print(f"[{now()}] 🛑 Đã thử login quá 3 lần vẫn bị chửi! Dừng lại báo Webhook thôi...")
                        webhook_url = os.environ.get("WEBHOOK_URL")
                        if webhook_url:
                            try:
                                payload = {
                                    "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                                    "task_code": "STEP_1_LOGIN_BLOCKED",
                                    "status": "failed",
                                    "data": {"worker_id": os.environ.get("WORKER_ID", "adminLuan031094")},
                                    "message": f"Tiktok chặn Login (Max Attempts) 3 lần liên tiếp. Cần vào RDP giải quyết."
                                }
                                r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                                print(f"[{now()}] 📲 Đã bắn Webhook gọi N8N báo LOGIN BLOCKED! (HTTP {r.status_code})")
                            except Exception as e:
                                print(f"[{now()}] ❌ Lỗi bắn Webhook báo Login Blocked: {e}")
                        break
                        
                    login_retry_count += 1
                    print(f"[{now()}] ⏳ Đang nghỉ mệt 10s rồi sẽ tự bấm lại lần thứ {login_retry_count}...")
                    time.sleep(10)
                    # Thử bấm Đăng nhập lại
                    login_btn = self.page.locator("button[type='submit']:has-text('Log in'), button[type='submit']")
                    if login_btn.count() > 0:
                        login_btn.first.click(force=True)
                        print(f"[{now()}] 🖱️ Đã thử force-click Đăng nhập lại!")
                    time.sleep(5)
                    continue
                
                # 2. Check 2FA OTP Screen
                if self.page.locator("text='Verify it’s really you'").count() > 0 or self.page.locator("text='Verify it's really you'").count() > 0 or self.page.locator("text='Xác minh danh tính'").count() > 0 or self.page.locator("text='Enter the 6-digit code'").count() > 0 or self.page.locator("text='Nhập mã gồm 6 chữ số'").count() > 0:
                    
                    # Nếu chưa bấm gửi Email -> bấm gửi Email (Chỉ bấm 1 lần)
                    email_option = self.page.locator("div:has-text('Email'), div:has-text('Thư điện tử')").last
                    if email_option.count() > 0 and not email_clicked:
                        print(f"[{now()}] 🛑 HỆ THỐNG YÊU CẦU XÁC MINH OTP (2FA)!")
                        email_option.click()
                        email_clicked = True
                        print(f"[{now()}] 📩 Đã bấm chọn xác minh qua Email. Chờ Tiktok gửi mã hoặc phản hồi Captcha...")
                        # Send webhook for OTP required
                        webhook_url = os.environ.get("WEBHOOK_URL")
                        if webhook_url and current_username: # Assuming current_username is email here
                            try:
                                payload = {
                                    "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                                    "task_code": "OTP_REQUIRED",
                                    "status": "waiting_otp",
                                    "data": {"email": current_username},
                                    "message": f"Tiktok yêu cầu mã gửi về mail {current_username}. Bot đang chờ 90s."
                                }
                                r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                                print(f"[{now()}] 📲 Đã bắn Webhook báo OTP REQUIRED! (HTTP {r.status_code})")
                                webhook_sent = True # Mark as sent to avoid resending
                            except Exception as e:
                                print(f"[{now()}] ❌ Lỗi gửi Webhook báo OTP Required: {e}")
                        time.sleep(3)
                        continue # Vòng lặp sẽ lặp lại để nhỡ có Captcha lòi ra thì nó giải
                        
                    # Gửi Webhook cho N8N biết đi check mail (Chỉ gửi 1 lần)
                    webhook_url = os.environ.get("WEBHOOK_URL")
                    if webhook_url and current_username and not webhook_sent and email_clicked:
                        try:
                            payload = {
                                "task_code": "STEP_2_WAITING_FOR_OTP",
                                "status": "pending",
                                "data": {"username": current_username},
                                "message": "Cần N8N check mail để lấy OTP và ghi vào code_verifier"
                            }
                            r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                            print(f"[{now()}] 📲 Đã bắn Webhook gọi N8N đi chọc Mail lấy OTP! (HTTP {r.status_code})")
                            webhook_sent = True
                        except Exception as e:
                            print(f"[{now()}] ❌ Lỗi gửi Webhook báo OTP: {e}")
                            
                    if email_clicked or self.page.locator("input[type='text'], input[type='number']").count() > 0:
                        print(f"[{now()}] ⏳ BOT đang túc trực đọc Database chờ mã OTP...")
                        otp_filled = False
                        
                        # Vòng lặp chờ OTP từ DB tối đa 60s (20 lần x 3s)
                        for _ in range(20):
                            # Nếu lúc đang chờ mã tự dưng bị dội Captcha (trường hợp hiếm)
                            captcha_loc_inner = self.page.locator(".captcha-verify-container, #captcha-verify-image")
                            if captcha_loc_inner.count() > 0 and captcha_loc_inner.first.is_visible():
                                print(f"[{now()}] ⚠️ Phát hiện Captcha overlay! Thoát vòng lặp chờ OTP để giải Captcha.")
                                break
                                
                            if current_username:
                                code = tiktok_db.get_tiktok_account_verifier(current_username)
                                if code and len(str(code)) >= 6:
                                    print(f"[{now()}] 🎉 ĐÃ BẮT ĐƯỢC MÃ OTP TỪ DB: {code}")
                                    try:
                                        otp_container = self.page.locator("input[type='text'], input[type='number']").first
                                        if otp_container.count() > 0:
                                            otp_container.click()
                                            self.page.keyboard.type(str(code))
                                            time.sleep(1)
                                            print(f"[{now()}] ⌨️ Đã nhập OTP vào form!")
                                            otp_filled = True
                                            tiktok_db.reset_tiktok_account_verifier(current_username)
                                            break
                                    except Exception as e:
                                        print(f"[{now()}] ❌ Lỗi khi điền OTP: {e}")
                            time.sleep(3)
                            
                        # Thoát vòng lặp chờ nếu OTP điền xong
                        if otp_filled:
                            time.sleep(5) # đơi xem có pass không
                            continue
                            
                time.sleep(2)
                
            print(f"[{now()}] ✅ Đã qua Ải Đăng Nhập!")
            self.needs_login = False
            self.page.goto(SHOWCASE_URL, timeout=60000, wait_until="domcontentloaded")
            time.sleep(3)

        # 2. Xử lý Captcha 2 Hình
        captcha_detected = False
        for _ in range(5):
            if self.page.locator("text='Verify to continue'").count() > 0 or self.page.locator("text='Xác minh để tiếp tục'").count() > 0 or self.page.locator("#captcha-verify-image").count() > 0:
                captcha_detected = True
                break
            time.sleep(1)
            
        if captcha_detected:
            print(f"[{now()}] ⚠️ [CẢNH BÁO] Hệ thống Tiktok dội Captcha hình ảnh!")
            solver_instance = PlaywrightCaptchaSolver(self.page)
            captcha_context = {
                'module_name': 'Affiliate_Web_Validator',
                'worker_id': os.environ.get("WORKER_ID", "adminLuan031094")
            }
            
            captcha_cleared = False
            for attempt in range(1, 4):
                print(f"[{now()}] 🤖 [BỐT GIẢI MÃ] Lần chọt {attempt}/3...")
                solver_instance.solve(captcha_context)
                time.sleep(3)
                
                if self.page.locator("text='Verify to continue'").count() == 0 and self.page.locator("text='Xác minh để tiếp tục'").count() == 0 and self.page.locator("#captcha-verify-image").count() == 0:
                    captcha_cleared = True
                    print(f"[{now()}] 🎉 BỐT GIẢI MÃ THÀNH CÔNG ở lần thử {attempt}!")
                    break
                    
                time.sleep(2)
            
            if not captcha_cleared:
                print(f"[{now()}] ⏳ BOT Giải mã thất bại. Vui lòng can thiệp tay!")
                for _ in range(300):
                    if self.page.locator("text='Verify to continue'").count() == 0 and self.page.locator("text='Xác minh để tiếp tục'").count() == 0 and self.page.locator("#captcha-verify-image").count() == 0:
                        break
                    time.sleep(1)
            
            print(f"[{now()}] ✅ Cổng Captcha đã mở!")
            time.sleep(3)

    def login_manual(self):
        """Mở trang chủ để đăng nhập thủ công và không tự đóng trình duyệt"""
        print(f"[{now()}] 🌍 Đang mở trang chủ TikTok Shop Creator (VN)...")
        self.page.goto("https://shop.tiktok.com/streamer/home?region=vn", timeout=60000, wait_until="domcontentloaded")
        print(f"[{now()}] 👉 TRÌNH DUYỆT ĐANG MỞ. Vui lòng đăng nhập vào tài khoản của bạn.")
        print(f"[{now()}] 🛑 Nhấn Ctrl+C ở Terminal này khi bạn đã đăng nhập xong để đóng trình duyệt an toàn.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[{now()}] 🟢 Đã xác nhận đăng nhập xong. Đang đóng trình duyệt...")

    def check_global_login(self):
        """Bước 1: Kiểm tra login toàn cục từ Tiktok"""
        print(f"[{now()}] 🌍 Bước 1: Kiểm tra phiên đăng nhập nền tảng tại TikTok.com...")
        try:
            self.page.goto("https://www.tiktok.com/login/phone-or-email/phone-password", timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"[{now()}] ⚠️ Lỗi khi tải trang login: {str(e)}")
            
        print(f"[{now()}] ⏳ Đang đợi 10s xem Tiktok có tự chuyển hướng (đã login) không...")
        try:
            # Chờ tối đa 10s để xem URL có đổi sang trang khác thay vì /login không
            self.page.wait_for_url(lambda url: "login" not in url.lower(), timeout=10000)
        except Exception:
            pass  # Nếu timeout thì báo lỗi hoặc chưa đăng nhập ở dưới

        if "login" in self.page.url.lower():
            self.needs_login = True
            self.ensure_logged_in_and_no_captcha()
        else:
            print(f"[{now()}] ✅ Tài khoản đã mở cửa sẵn phiên đăng nhập nền tảng. URL hiện tại: {self.page.url}")

    def scrape_showcase(self):
        """Web automation workflow để lôi danh sách Showcase"""
        self.check_global_login()
        
        print(f"[{now()}] 🌍 Bước 2: Đang truy cập Showcase: {SHOWCASE_URL}")
        self.page.goto(SHOWCASE_URL, timeout=60000, wait_until="domcontentloaded")
        self.ensure_logged_in_and_no_captcha()
        
        print(f"[{now()}] 🔄 Đang ép tải lại trang để bắt API Showcase mới nhất...")
        self.page.reload(wait_until="domcontentloaded")
        
        page_num = 1
        while True:
            print(f"[{now()}] ⏳ [TRANG {page_num}] Chờ tối đa 20s để chặn API Showcase Data...")
            for _ in range(20):
                if len(self.collected_showcase_products) > 0:
                    break
                time.sleep(1)
                
            if not self.collected_showcase_products:
                print(f"[{now()}] ⚠️ Không vớt được data showcase nào ở trang {page_num} sau 10s. Có thể Showcase rỗng, hoặc mạng chậm.")
                break

            # --- BẮT ĐẦU LOGIC ĐỒNG BỘ SHOWCASE ---
            print(f"[{now()}] ⚙️ Bắt đầu tiến trình Đồng Bộ (Sync) Showcase với Cơ Sở Dữ Liệu ở trang {page_num}...")
            
            # Khởi tạo Showcase ID động chạy theo Account ID thay vì nhốt cứng = 1
            current_account_id = os.environ.get("TIKTOK_ACCOUNT_ID", 1)
            active_showcase_id = tiktok_db.get_or_create_showcase_by_account(current_account_id)
            
            # Lấy danh sách ID đã duyệt
            db_product_states = tiktok_db.get_all_showcase_product_states(showcase_id=active_showcase_id)
            print(f"[{now()}] 📥 Đã tải {len(db_product_states)} Product ID từ Database (Showcase ID: {active_showcase_id}).")
            
            # Tạo bản sao list hiện tại để duyệt
            products_to_process = self.collected_showcase_products.copy()
            
            for p in products_to_process:
                pid = str(p.get('product_id'))
                name = p.get('title', 'Unknown')
                price_info = p.get('price', {})
                # Phụ thuộc vào cấu trúc thực tế của JSON báo trả về (price, format_price, stock_num, status...)
                price = p.get('discount_price', p.get('price', 0)) 
                if isinstance(price, dict): # Gỡ thêm nếu nó bọc dict bên trong
                    price = price.get('price_val', 0)
                
                stock = p.get('stock_num', 0)
                is_live = (p.get('status') == 1 or p.get('stock_status') == 1) # Giả định status
                
                if pid in db_product_states:
                    is_db_live = db_product_states[pid]
                    if is_db_live:
                        print(f"[{now()}] ✔️ Khớp DB: {pid} - {name[:20]}... Đang UPSERT trạng thái.")
                        tiktok_db.upsert_showcase_item(showcase_id=active_showcase_id, product_id=pid, product_name=name, price=price, stock=stock, is_live=True)
                    else:
                        print(f"[{now()}] ⏭️ Sản phẩm {pid} đã bị ẨN trong DB trước đó, bỏ qua click UI.")
                else:
                    print(f"[{now()}] ❌ KHÔNG KHỚP DB: {pid} - {name[:20]}... Chuẩn bị ẨN (Hide) khỏi Showcase!")
                    # Lưu ý: Tìm Row chứa product_id thông qua attr data-exposure-key
                    try:
                         row_locator = self.page.locator(f"tr[data-exposure-key='{pid}']")
                         if row_locator.count() > 0:
                             hide_btn = row_locator.locator("span.arco-link:has-text('Hide'), span.arco-link:has-text('Ẩn')").first
                             if hide_btn.count() > 0:
                                 hide_btn.click()
                                 print(f"[{now()}] 👉 Đã click nút ẨN cho sản phẩm {pid}.")
                                 tiktok_db.upsert_showcase_item(showcase_id=active_showcase_id, product_id=pid, product_name=name, price=price, stock=stock, is_live=False)
                                 self.page.wait_for_timeout(1000) # Chờ thao tác ẩn thành công
                             else:
                                 print(f"[{now()}] ⚠️ Tồn tại dòng {pid} nhưng KHÔNG tìm thấy nút Ẩn (Hide).")
                                 tiktok_db.upsert_showcase_item(showcase_id=active_showcase_id, product_id=pid, product_name=name, price=price, stock=stock, is_live=False) # Ghi nhận đè
                         else:
                             print(f"[{now()}] ⚠️ Không tìm thấy dòng sản phẩm {pid} (tr[data-exposure-key]) trên màn hình để ẩn.")
                    except Exception as e:
                         print(f"[{now()}] ❌ Lỗi khi thao tác Ẩn sản phẩm {pid}: {e}")
                         
            print(f"[{now()}] 🏁 Hoàn tất Tiến trình Đồng Bộ Showcase cho trang {page_num}.")
            self.collected_showcase_products.clear()
            
            # --- XỬ LÝ PHÂN TRANG (PAGINATION) ---
            next_btn = self.page.locator("li.arco-pagination-item-next")
            if next_btn.count() > 0:
                # Kiểm tra nút Next có bị disable không (Disabled = Trang cuối)
                is_disabled = "arco-pagination-item-disabled" in next_btn.get_attribute("class") or next_btn.evaluate("el => el.classList.contains('arco-pagination-item-disabled')")
                if not is_disabled:
                    print(f"[{now()}] ➡️ Chuyển sang trang tiếp theo (Trang {page_num + 1})...")
                    next_btn.click()
                    page_num += 1
                    self.page.wait_for_timeout(3000) # Chờ 3s để Next Page gọi API /showcase_product/list mới, interceptor sẽ hứng
                else:
                    print(f"[{now()}] 🛑 Đã đến trang cuối cùng của Showcase.")
            else:
                 print(f"[{now()}] 🛑 Không tìm thấy nút Next phân trang trên giao diện, kết thúc lặp.")
                 break

    def check_commission_by_url(self, product_url, action="cancel"):
        """Dán link vào khung Add Product để xem trước Hoa hồng mà không cần duyệt web hên xui"""
        print(f"[{now()}] 🔍 Bắt đầu check URL: {product_url}")
        self.checking_product_id = product_url.split("/")[-1]
        self.last_commission_data = None
        
        try:
            # 1. Bấm nút "Add new product" (Tùy thuộc vào ngôn ngữ trình duyệt)
            search_input = self.page.locator("input[placeholder*='URL'], input[placeholder*='Liên kết']").first
            is_drawer_open = search_input.count() > 0 and search_input.is_visible()
            
            if not is_drawer_open:
                add_btn = self.page.locator("button:has-text('Add new product'), button:has-text('Thêm sản phẩm mới')").first
                if add_btn.count() > 0:
                    print(f"[{now()}] 👆 Bấm nút 'Thêm sản phẩm mới'...")
                    add_btn.click()
                    time.sleep(2)
                else:
                    # Nếu không thấy nút dạng button, tìm div/span có chữ tương tự
                    fallback_btn = self.page.locator("text='Add new product', text='Thêm sản phẩm mới'").first
                    if fallback_btn.count() > 0:
                         print(f"[{now()}] 👆 Bấm vào text 'Thêm sản phẩm mới'...")
                         fallback_btn.click()
                         time.sleep(2)
                    else:
                         print(f"[{now()}] ❌ Không tìm thấy nút Thêm sản phẩm. Có thể giao diện đã thay đổi.")
                         return None
            else:
                 print(f"[{now()}] ℹ️ Khung nhập URL đã mở sẵn, tiến hành dán link...")
                 # Xóa link cũ nếu có
                 search_input.fill("")
                 time.sleep(0.5)
            
            # 2. Tìm ô Input "Enter product URL" và dán link
            search_input = self.page.locator("input[placeholder*='URL'], input[placeholder*='Liên kết']").first
            if search_input.count() > 0:
                print(f"[{now()}] ⌨️ Nhập URL sản phẩm vào ô tìm kiếm...")
                search_input.fill(product_url)
                time.sleep(1)
                
                print(f"[{now()}] � Tìm và click thẻ Primary Button 'URL sản phẩm' hoặc 'Product URL'...")
                self.last_commission_data = None
                
                # Bắt chính xác nút bấm (Loại trừ các Tab trùng tên nhờ thẻ arco-btn-primary)
                submit_btn = self.page.locator("button.arco-btn-primary:has-text('URL sản phẩm'), button.arco-btn-primary:has-text('Product URL')").first
                if submit_btn.count() > 0:
                    submit_btn.click()
                else:
                    print(f"[{now()}] ⚠️ Không tìm thấy nút Submit dạng primary. Ấn Enter làm dự phòng...")
                    search_input.press("Enter")
                
                print(f"[{now()}] ⏳ Đã nhấn xác nhận Link, chờ Server phản hồi API product_link/check...")
            else:
                 print(f"[{now()}] ❌ Không tìm thấy ô nhập URL.")
                 return None
            for _ in range(15):
                # Check directly on the UI for non-affiliate warning text
                not_affiliate_msg = self.page.locator("text='Đây không phải là sản phẩm liên kết', text='This is not an affiliate product'").first
                if not_affiliate_msg.count() > 0:
                     print(f"[{now()}] ⚠️ Phát hiện cảnh báo UI: Đây không phải là sản phẩm liên kết!")
                     cancel_btn = self.page.locator("button:has-text('Cancel'), button:has-text('Hủy')").first
                     if cancel_btn.count() > 0 and cancel_btn.is_visible():
                         cancel_btn.click()
                     else:
                         self.page.keyboard.press("Escape")
                     time.sleep(1)
                     return "NOT_AFFILIATE"

                if self.last_commission_data is not None:
                     print(f"[{now()}] 🎉 BẮT ĐƯỢC HOA HỒNG TỪ API!")
                     
                     if action == "add":
                         # Bấm Add / Thêm vào cửa hàng
                         add_submit_btn = self.page.locator(".arco-drawer button.pc_add_product, .arco-drawer button:has-text('Add to showcase'), .arco-drawer button:has-text('Thêm vào cửa hàng'), .arco-drawer button:has-text('Thêm sản phẩm')").first
                         if add_submit_btn.count() == 0:
                             add_submit_btn = self.page.locator("button.pc_add_product, button:has-text('Add to showcase'), button:has-text('Thêm vào cửa hàng'), button:has-text('Thêm sản phẩm')").first
                             
                         if add_submit_btn.count() > 0 and add_submit_btn.is_visible():
                             print(f"[{now()}] 🛒 Đã nhấn nút 'Thêm vào cửa hàng' cho Sản phẩm hot.")
                             try:
                                 add_submit_btn.click(force=True, timeout=5000)
                             except Exception as e:
                                 print(f"[{now()}] ⚠️ Click bình thường lỗi ({e}), thử dùng Javascript...")
                                 self.page.evaluate("arguments[0].click()", add_submit_btn.element_handle())
                             
                             time.sleep(2) # Chờ nó add xong
                             print(f"[{now()}] 🔄 Đang tải lại trang Showcase để đóng dứt điểm Drawer...")
                             self.page.reload(timeout=60000, wait_until="domcontentloaded")
                             time.sleep(3)
                         else:
                             print(f"[{now()}] ⚠️ Không tìm thấy nút Add to showcase! Giao diện có thể đã đổi hoặc SP đã trong Showcase.")
                     else:
                         # Bấm hủy/đóng popup để dọn dẹp cho lần check tới TẤT CẢ ACTION
                         cancel_btn = self.page.locator("button:has-text('Cancel'), button:has-text('Hủy')").first
                         if cancel_btn.count() > 0 and cancel_btn.is_visible():
                             cancel_btn.click()
                         else:
                             self.page.keyboard.press("Escape")
                         time.sleep(1)
                     
                     return self.last_commission_data
                # Quan trọng: Không dùng time.sleep(1) vì sẽ block Thread chặn sự kiện on('response')
                self.page.wait_for_timeout(1000)
                
            print(f"[{now()}] ⏳ Timeout: Không nhận được dữ liệu Hoa hồng từ gói tin mạng.")
            return None
            
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi khi thao tác check Commission: {e}")
            return None

    def extract_product_description_html(self, product_url):
        """Dùng Playwright (tab mới) để vượt CAPTCHA và cào Description JSON từ cấu trúc HTML"""
        try:
            print(f"[{now()}] 🌐 Bắt đầu cào trực tiếp Description qua Tab phụ cho: {product_url}")
            
            # Sử dụng Playwright context có sẵn để mở tab phụ
            new_page = self.page.context.new_page()
            
            try:
                new_page.goto(product_url, timeout=15000, wait_until="domcontentloaded")
                time.sleep(2) # Chờ 1 chút để DOM ổn định
                
                # --- XỬ LÝ CAPTCHA TRÊN TAB PHỤ ---
                captcha_locator = new_page.locator(".captcha-verify-container, #captcha-verify-image")
                if captcha_locator.count() > 0 and captcha_locator.first.is_visible():
                    print(f"[{now()}] ⚠️ Phát hiện Captcha trên Tab chi tiết sản phẩm! Đang gọi BỐT...")
                    solver_instance = PlaywrightCaptchaSolver(new_page)
                    captcha_context = {
                        'module_name': 'Affiliate_Web_Validator_Desc',
                        'worker_id': os.environ.get("WORKER_ID", "adminLuan031094")
                    }
                    for attempt in range(1, 6):
                        print(f"[{now()}] 🤖 [BỐT GIẢI MÃ TAB PHỤ] Lần chọt {attempt}/5...")
                        solver_instance.solve(captcha_context)
                        time.sleep(3)
                        # Check xem captcha đã biến mất chưa
                        if new_page.locator(".captcha-verify-container, #captcha-verify-image").count() == 0 or not new_page.locator(".captcha-verify-container, #captcha-verify-image").first.is_visible():
                            print(f"[{now()}] 🎉 BỐT GIẢI MÃ TAB PHỤ THÀNH CÔNG ở lần thử {attempt}!")
                            break
                        time.sleep(2)
                    time.sleep(2) # Chờ redirect/load trang HTML thật sự sau khi giải Captcha
                
                # Trích xuất nội dung HTML
                html_content = new_page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Giải thuật cũ: Tìm thẻ script JSON
                script_tag = soup.find('script', id='__MODERN_ROUTER_DATA__', type='application/json')
                
                if script_tag and script_tag.string:
                    try:
                        data = json.loads(script_tag.string)
                        queries = data.get("queries", [])
                        loader_data = data.get("loaderData", {})
                        
                        initial_data = {}
                        if queries:
                            initial_data = queries[0].get("initialData", {})
                        elif loader_data:
                            # TikTok new struct: data -> loaderData -> (name$)/(id)/page -> initialData
                            page_data = loader_data.get("(name$)/(id)/page", {})
                            initial_data = page_data.get("initialData", {})
                            
                        if initial_data:
                            # Tùy theo cấu trúc cũ/mới, product_base có thể nằm trực tiếp hoặc trong productInfo
                            product_base = initial_data.get("product_base")
                            if not product_base:
                                product_info = initial_data.get("productInfo", {})
                                product_base = product_info.get("product_base", {})
                                
                            desc_detail = product_base.get("desc_detail", "")
                            
                            if desc_detail:
                                # --- CLEAN DESCRIPTION (GIỮ LẠI CHỮ THUẦN) ---
                                try:
                                    # Nếu nó là chuỗi JSON, parse nó thành list/dict
                                    if isinstance(desc_detail, str):
                                        try:
                                            parsed_desc = json.loads(desc_detail)
                                        except json.JSONDecodeError:
                                            parsed_desc = desc_detail # Không phải JSON, giữ nguyên chuỗi
                                    else:
                                        parsed_desc = desc_detail
                                        
                                    if isinstance(parsed_desc, list):
                                        import re
                                        # Lọc chỉ lấy phần tử có type='text' và có giá trị text
                                        text_parts = [d.get('text', '') for d in parsed_desc if d.get('type') == 'text' and d.get('text')]
                                        clean_text = ' '.join(text_parts)
                                        # Xóa khoảng trắng thừa
                                        clean_desc = re.sub(r'\s+', ' ', clean_text).strip()
                                        if clean_desc:
                                            desc_detail = clean_desc
                                        # Nếu lọc xong rỗng (toàn ảnh chẳng hạn), có thể trả về string rỗng hoặc giữ nguyên
                                        elif not clean_desc and text_parts == []:
                                            desc_detail = ""
                                except Exception as e:
                                    print(f"[{now()}] ⚠️ Lỗi trong quá trình dọn dẹp Description: {e}")
                                # ---------------------------------------------

                                print(f"[{now()}] ✅ Trích xuất Description bằng Playwright Tab thành công ({len(desc_detail)} chars)!")
                                return desc_detail
                            else:
                                print(f"[{now()}] ⚠️ Không tìm thấy 'desc_detail' trong luồng JSON gốc.")
                        else:
                             print(f"[{now()}] ⚠️ Không tìm thấy 'queries' hay 'loaderData' trong __MODERN_ROUTER_DATA__.")
                    except json.JSONDecodeError:
                        print(f"[{now()}] ❌ Lỗi decode JSON từ script tag __MODERN_ROUTER_DATA__.")
                else:
                    print(f"[{now()}] ❌ Không tìm thấy thẻ <script id='__MODERN_ROUTER_DATA__'> trên trang (Tab phụ).")
                    pass
            finally:
                # Đóng tab phụ sau khi cào xong (tránh tốn ram)
                new_page.close()
                
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi extract_product_description_html: {e}")
            
        return ""

    def process_high_sales_commissions(self):
        """Lấy các sản phẩm có lượt bán cao, tự động điền URL và bắt API Hoa Hồng"""
        print(f"[{now()}] ⚙️ Bắt đầu tiến trình kiểm tra Hoa hồng hàng loạt cho sản phẩm hot...")
        products_to_check = tiktok_db.get_high_sales_products_to_check(min_sales=50)
        
        if not products_to_check:
            print(f"[{now()}] 🟢 Không có sản phẩm nào cần check hoa hồng hôm nay.")
            return
            
        print(f"[{now()}] 📥 Đã tải {len(products_to_check)} sản phẩm cần check từ DB.")
        
        # Cần ở đúng trang Showcase
        if "showcase" not in self.page.url.lower():
             self.page.goto(SHOWCASE_URL, timeout=60000, wait_until="domcontentloaded")
             time.sleep(2)
             
        for p in products_to_check:
            tiktok_id = p['tiktok_product_id']
            description_db = p.get('description')
            product_url = f"https://shop.tiktok.com/view/product/{tiktok_id}"
            
            # --- TÍCH HỢP TASK 14: LẤY MÔ TẢ QUA HTTP ---
            if not description_db or not str(description_db).strip():
                description = self.extract_product_description_html(product_url)
                if description:
                    tiktok_db.update_product_description(tiktok_id, description)
            else:
                print(f"[{now()}] ⏭️ Sản phẩm {tiktok_id} đã có Description trong DB, bỏ qua bước lấy mô tả qua Tab phụ.")
            
            commission_data = self.check_commission_by_url(product_url)
            
            if commission_data == "NOT_AFFILIATE":
                 print(f"[{now()}] 🚫 Sản phẩm {tiktok_id} không hỗ trợ Affiliate. Cập nhật is_affiliate = False.")
                 tiktok_db.update_product_commission(tiktok_id, 0.0, 0, is_affiliate=False)
                 time.sleep(3)
                 continue
                 
            if commission_data:
                 # Bóc nội dung json
                 try:
                     results = commission_data.get('data', {}).get('results', [])
                     if results:
                         product_info = results[0].get('product_info', {})
                         closed_loop_product = product_info.get('closed_loop_product', {})
                         affiliate_info = closed_loop_product.get('affiliate_info')
                         
                         if affiliate_info:
                             # Có hoa hồng
                             rate_percent = affiliate_info.get('commission_rate', 0) / 100.0 # 500 -> 5.0%
                             
                             # Extract price correctly (from format_price or similar)
                             price_str = closed_loop_product.get('format_price', '0')
                             price_str = price_str.replace('₫', '').replace('.', '').replace(',', '')
                             try:
                                 price_val = int(price_str)
                             except:
                                 price_val = 0
                             
                             # They might have est_commission_expense too, but let's recalculate to be exact
                             amount = int(price_val * (rate_percent / 100))
                             if amount == 0:
                                 amount_str = str(affiliate_info.get('est_commission_expense', '0')).replace('₫', '').replace('.', '').replace(',', '')
                                 try:
                                      amount = int(amount_str)
                                 except:
                                      amount = 0
                                  
                             print(f"[{now()}] 💰 Cập nhật Affiliate: Giá: {price_val}đ - Hoa hồng: {rate_percent}% - Tiền hh: {amount}VNĐ")
                             tiktok_db.update_product_commission(tiktok_id, rate_percent, amount, is_affiliate=True)
                         else:
                             # Không có hoa hồng
                             print(f"[{now()}] 📉 Cập nhật Non-Affiliate. Dữ liệu gốc: {json.dumps(commission_data, ensure_ascii=False)[:300]}...")
                             pass
                             tiktok_db.update_product_commission(tiktok_id, 0.0, 0, is_affiliate=False)
                     else:
                          print(f"[{now()}] ❓ Không có mảng kết quả từ gói tin.")
                 except Exception as e:
                     print(f"[{now()}] ❌ Lỗi bóc tách JSON hoa hồng: {e}")
            else:
                 print(f"[{now()}] ☹️ Không lấy được gói tin cho {tiktok_id}.")
                 
            print(f"[{now()}] ⏸️ Nghỉ 3s trước khi check món tiếp theo...")     
            time.sleep(3) # Tránh bị rate limit

    def process_add_to_showcase_from_ai(self):
        """(Bước 5) Lấy các sản phẩm có điểm AI cao và Add vào Showcase. Sau đó lập lịch chạy Tool Video"""
        print(f"[{now()}] 🌟 [BƯỚC 5] Bắt đầu thêm Sản phẩm đủ điều kiện (is_video_ready) vào Showcase...")
        
        current_account_id = os.environ.get("TIKTOK_ACCOUNT_ID", 1)
        active_showcase_id = tiktok_db.get_or_create_showcase_by_account(current_account_id)
        
        vip_products = tiktok_db.get_high_ai_score_products(limit=10)
        
        if not vip_products:
             print(f"[{now()}] 🟢 Không có sản phẩm nào đủ điều kiện lên Video để Add hôm nay.")
             return
             
        print(f"[{now()}] 📥 Đã tìm thấy {len(vip_products)} sản phẩm (is_video_ready) tiềm năng từ AI.")
        
        # Cần ở đúng trang Showcase
        if "showcase" not in self.page.url.lower():
             self.page.goto(SHOWCASE_URL, timeout=60000, wait_until="domcontentloaded")
             time.sleep(2)
             
        for p in vip_products:
            tiktok_id = p['tiktok_id']
            internal_id = p['internal_id']
            title = p['title']
            print(f"[{now()}] 🚀 Đang Add: [{tiktok_id}] {title[:30]}...")
            
            product_url = f"https://shop.tiktok.com/view/product/{tiktok_id}"
            
            # Sử dụng hàm check_commission có sẵn nhưng truyền lệnh 'add' thay vì 'cancel'
            res = self.check_commission_by_url(product_url, action="add")
            
            if res != "NOT_AFFILIATE":
                new_item_id = p.get('showcase_item_id') # Fallback
                # Thực hiện đồng bộ tay vào bảng aff_showcase_items ngay khi Add xong (Task 17)
                try:
                    new_item_id = tiktok_db.upsert_showcase_item(
                        showcase_id=active_showcase_id,
                        product_id=tiktok_id,
                        product_name=title,
                        price=p.get('sale_price', 0),
                        stock=999,
                        is_live=True
                    ) or new_item_id
                    print(f"[{now()}] 🔄 Đã đồng bộ tay Sản phẩm {tiktok_id} vào Bảng Showcase. (ID: {new_item_id})")
                except Exception as sync_err:
                    print(f"[{now()}] ❌ Lỗi đồng bộ tay bảng Showcase cho {tiktok_id}: {sync_err}")
            
                # Ghi nhận vào DB Table Campaign Video
                camp_id = tiktok_db.create_video_campaign(
                    product_id=internal_id,
                    gender=p.get('gender'),
                    product_type_id=p.get('product_type_id'),
                    showcase_item_id=new_item_id,
                    ai_prompt=p.get('ai_prompt'),
                    tiktok_product_id=tiktok_id,
                    tiktok_id=os.environ.get("TIKTOK_ACCOUNT_ID")
                )
            if camp_id:
                print(f"[{now()}] 🎬 Đã lên lịch tạo Video Campaign (ID: {camp_id}) cho tham chiếu sản phẩm: {internal_id}.")
            else:
                print(f"[{now()}] ⚠️ Campaign cho {internal_id} (Tiktok ID: {tiktok_id}) hình như đã tồn tại rồi.")
            
            print(f"[{now()}] ⏸️ Nghỉ 5s tránh Rate Limit...")
            time.sleep(5)
            
        print(f"[{now()}] 🎉 Hoàn tất tiến trình thêm Sản phẩm VIP vào Showcase!")

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    import sys
    import os
    
    import sys
    import os
    
    tiktok_account_id = os.environ.get("TIKTOK_ACCOUNT_ID")
    if not tiktok_account_id:
        print(f"[{now()}] ❌ Thiếu biến môi trường TIKTOK_ACCOUNT_ID. Bắt buộc gọi từ Gateway hoặc truyền N8N!")
        sys.exit(1)
        
    print(f"======================================================")
    print(f"   TIKTOK WEB AFFILIATE VALIDATOR - ACCOUNT ID: {tiktok_account_id}   ")
    print(f"======================================================")
    
    # Lấy data account từ Affiliate DB thay vì từ client_registry
    acc_data = tiktok_db.get_tiktok_account_by_id(tiktok_account_id)
    if not acc_data or not acc_data.get('chrome_profile_folder'):
        print(f"[{now()}] ❌ Không tìm thấy Profile Chrome trong bảng tiktok_accounts cho ID = {tiktok_account_id}.")
        sys.exit(1)
        
    folder = acc_data['chrome_profile_folder']
    
    # Luôn khởi chạy nằm ở Folder phân lập của Admin Scraper
    ADMIN_CHROME_BASE = r"D:\ChromeAutomation\AdminScraperProfiles"
    profile_absolute_path = os.path.join(ADMIN_CHROME_BASE, folder)
    print(f"[{now()}] 🔍 Đã liên kết với Admin Profile: {profile_absolute_path}")
    
    val = WebAffiliateValidator(profile_absolute_path)
    if len(sys.argv) > 1 and sys.argv[1] == "--test-login":
        val.is_test_login = True
        
    try:
        val.start_context()
        if len(sys.argv) > 1 and sys.argv[1] == "login":
            val.login_manual()
        elif len(sys.argv) > 1 and sys.argv[1] == "add_showcase":
            # TIẾN TRÌNH 2: BƯỚC 5 N8N (ADD TO SHOWCASE)
            val.process_add_to_showcase_from_ai()
            print(f"[{now()}] 🎉 Hoàn tất quy trình Bước 5.")
            
            # Gửi Webhook thành công Bước 5
            webhook_url = os.environ.get("WEBHOOK_URL")
            if webhook_url:
                try:
                    payload = {
                        "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                        "task_code": "STEP_5_ADD_SHOWCASE",
                        "status": "success",
                        "data": {},
                        "message": "Hoàn tất Add to Showcase và Setup Campaign Video"
                    }
                    import json
                    r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                    print(f"[{now()}] 📲 Đã gửi Webhook N8N (Bước 5)! (HTTP {r.status_code})")
                except Exception as e:
                    print(f"[{now()}] ❌ Lỗi gửi Webhook Bước 5: {e}")
            time.sleep(3)
        elif len(sys.argv) > 1 and sys.argv[1] == "check_commission":
            # TIẾN TRÌNH 3: BƯỚC 3 N8N (CHECK HOA HỒNG ĐA LUỒNG BẰNG WEB TOOL)
            val.process_high_sales_commissions()
            print(f"[{now()}] 🎉 Hoàn tất quy trình Bước 3.")
            
            # Gửi Webhook thành công Bước 3
            webhook_url = os.environ.get("WEBHOOK_URL")
            if webhook_url:
                try:
                    payload = {
                        "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                        "task_code": "STEP_3_COMMISSION_CHECK",
                        "status": "success",
                        "data": {},
                        "message": "Hoàn tất quét hoa hồng với Playwright Validator"
                    }
                    import json
                    r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                    print(f"[{now()}] 📲 Đã gửi Webhook N8N (Bước 3)! (HTTP {r.status_code})")
                except Exception as e:
                    print(f"[{now()}] ❌ Lỗi gửi Webhook Bước 3: {e}")
            time.sleep(3)
        else:
            # TIẾN TRÌNH 1: BƯỚC 2 N8N (CHỈ SYNC SHOWCASE)
            val.scrape_showcase()
            # Bỏ check hoa hồng vì đã làm riêng bên Bước 3
            print(f"[{now()}] 🎉 Hoàn tất toàn bộ chu trình Affiliate Validator.")
            
            # Gửi Webhook thành công Bước 2
            webhook_url = os.environ.get("WEBHOOK_URL")
            if webhook_url:
                try:
                    payload = {
                        "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                        "task_code": "STEP_2_SHOWCASE_SYNC",
                        "status": "success",
                        "data": {},
                        "message": "Hoàn tất đồng bộ Showcase và kiểm tra hoa hồng Web"
                    }
                    import json
                    r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                    print(f"[{now()}] 📲 Đã gửi Webhook N8N (Bước 2)! (HTTP {r.status_code})")
                except Exception as e:
                    print(f"[{now()}] ❌ Lỗi gửi Webhook Bước 2: {e}")
                    
            time.sleep(3)
    except Exception as e:
        traceback.print_exc()
        
        # Webhook lỗi
        webhook_url = os.environ.get("WEBHOOK_URL")
        if webhook_url:
            try:
                task_code = "STEP_5_ADD_SHOWCASE" if (len(sys.argv) > 1 and sys.argv[1] == "add_showcase") else "STEP_3_COMMISSION_CHECK" if (len(sys.argv) > 1 and sys.argv[1] == "check_commission") else "STEP_2_SHOWCASE_SYNC"
                payload = {
                    "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                    "task_code": task_code,
                    "status": "error",
                    "data": {"error": str(e)},
                    "message": f"Có lỗi bất ngờ khi chạy Validator: {task_code}"
                }
                import json
                requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
            except:
                pass
    finally:
        val.close_context()
