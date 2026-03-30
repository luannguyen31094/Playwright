import os
import sys
import time
import json
import traceback
import re
import requests
import jmespath
from playwright.sync_api import sync_playwright

# Setup paths to import Core
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

from Core.db_manager import get_worker_full_config
from Core.database_info import get_sys_var
import Tools.TiktokScraper.tiktok_db as tiktok_db

def now(): return time.strftime('%H:%M:%S')

# --- GLOBALS ---
total_scraped_items = 0

# --- CONFIG ---
WORKER_ID = os.environ.get("WORKER_ID", "Worker_01")
CATEGORY_URL = os.environ.get("CATEGORY_URL", "https://www.tiktok.com/shop/vn/category/menswear-underwear-824328")
USER_DATA_DIR_BASE = get_sys_var('ROOT_PATH', r'D:\ChromeAutomation')

# Constants for scraping
TARGET_API = "api/shop/vn/homepage_desktop/products_by_category"

def process_product_data(products, source_label="API"):
    """Xử lý danh sách sản phẩm và đẩy vào Database Affiliate"""
    global total_scraped_items
    if not products:
        return
        
    print(f"[{now()}] ⚙️ Bắt đầu xử lý {len(products)} sản phẩm từ {source_label}...")
    success_count = 0
        
    for item in products:
        try:
            # Tiktok API returns a dict. We extract what we need
            product_id = item.get("product_id") or str(item.get("id"))
            
            seller_info = item.get("seller_info", {})
            shop_id = item.get("seller_id") or seller_info.get("seller_id") or "unknown"
            shop_name = item.get("seller_name") or seller_info.get("shop_name", "Unknown Shop")
            title = item.get("title", "")
            
            # Extract Logo
            logo_url = ""
            shop_logo_obj = seller_info.get("shop_logo", {})
            if "url_list" in shop_logo_obj and len(shop_logo_obj["url_list"]) > 0:
                logo_url = shop_logo_obj["url_list"][0]
                
            # Extract Canonical URL
            canonical_url = ""
            seo_url = item.get("seo_url", {})
            if "canonical_url" in seo_url:
                canonical_url = seo_url["canonical_url"]
            
            # Extract images
            images = []
            if "images" in item and isinstance(item["images"], list):
                # Format 1
                images = [img.get("url_list", [None])[0] for img in item["images"] if img.get("url_list")]
            elif "image" in item:
                # Format 2
                img_obj = item["image"]
                if "url_list" in img_obj:
                     images = img_obj["url_list"]
            
            # Extract metrics
            price_info = item.get("product_price_info", {})
            sold_info = item.get("sold_info", {})
            rate_info = item.get("rate_info", {})
            
            metric_payload = {
                "sale_price_decimal": price_info.get("sale_price_decimal", 0) or (item.get("price", {}).get("real_price", 0)),
                "origin_price_decimal": price_info.get("origin_price_decimal", 0),
                "discount_decimal": price_info.get("discount_decimal", 0),
                "sold_count": sold_info.get("sold_count", 0) or item.get("sales", 0) or item.get("sale_count", 0),
                "rating_score": rate_info.get("score", 0),
                "review_count": rate_info.get("review_count", 0)
            }
                
             # Upsert Shop & Product
            product_payload = {
                "product_id": product_id,
                "shop_id": shop_id,
                "shop_name": shop_name,
                "shop_logo": logo_url,
                "title": title,
                "image_urls": images,
                "canonical_url": canonical_url
            }
            
            # Extract Category dynamically from CATEGORY_URL
            import re
            slug = "unknown"
            tiktok_category_id = "unknown"
            
            match_c = re.search(r'/c/([^/]+)/(\d+)', CATEGORY_URL)
            if match_c:
                slug = match_c.group(1)
                tiktok_category_id = match_c.group(2)
            else:
                match_cat = re.search(r'/category/(.*?)-(\d+)(?:/|\?|$)', CATEGORY_URL)
                if match_cat:
                    slug = match_cat.group(1)
                    tiktok_category_id = match_cat.group(2)
                    
            category_id = tiktok_db.get_or_create_category(slug, tiktok_category_id)
            
            # Cập nhật Category ID vào thẳng tài khoản TikTok đang đi cào (TASK N8N)
            current_account_id = os.environ.get("TIKTOK_ACCOUNT_ID")
            if current_account_id:
                tiktok_db.update_tiktok_account_category(current_account_id, category_id)
            
            internal_product_id = tiktok_db.upsert_product(product_payload, category_id)
            
            if internal_product_id:
                # Insert into aff_product_analysis
                tiktok_db.upsert_product_analysis(product_payload, metric_payload)
                success_count += 1
            # print(f"[{now()}] 📥 Đã Insert/Update sản phẩm: {title[:30]}... (Shop: {shop_name})")
            
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi xử lý item TikTok (ID: {product_id if 'product_id' in locals() else 'Unknown'}): {e}")
            
    print(f"[{now()}] ✅ Hoàn tất đẩy {success_count}/{len(products)} sản phẩm vào Database (Từ {source_label})!")
    
    global total_scraped_items
    total_scraped_items += success_count

class TiktokScraper:
    def __init__(self, browser_profile_path):
        self.profile_path = browser_profile_path
        self.playwright = None
        self.browser_context = None
        self.page = None
        self.click_count = 0

    def start_context(self):
        """Khởi tạo Chromium với Profile sẵn có của hệ thống"""
        print(f"[{now()}] 🚀 Mở trình duyệt ẩn danh sử dụng Profile: {self.profile_path}")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_path,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ]
        )
        
        # Use the first page created by persistent context instead of opening a new one
        pages = self.browser.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = self.browser.new_page()
            
        # Đăng ký sự kiện Interceptor bắt trộm Network API
        self.page.on("response", self.handle_api_response) # Kept original handler name

    def close_context(self):
        """Dọn dẹp RAM"""
        if self.browser: # Changed from browser_context
            self.browser.close() # Changed from browser_context
        if self.playwright:
            self.playwright.stop()
        print(f"[{now()}] 🧹 Đã giải phóng RAM, đóng Context.")

    def handle_api_response(self, response):
        """Module B: Đánh chặn API (Network Interceptor)"""
        try:
            url = response.url
            if TARGET_API in url and response.status == 200:
                print(f"[{now()}] 📡 [INTERCEPT] Bắt được gói tin API Xem Thêm từ Tiktok!")
                # TikTok có thể trả về gzipped hoặc brotli json
                body = response.json()
                
                # Trích xuất products
                data_obj = body.get("data", {})
                products = data_obj.get("products") or data_obj.get("productList", [])
                
                if products:
                    print(f"[{now()}] 📦 [API] Lược trích được {len(products)} sản phẩm. Bơm vào Database!")
                    process_product_data(products, source_label="API Xem Thêm")
                else:
                    data_keys = list(data_obj.keys()) if isinstance(data_obj, dict) else "Không có phần tử data"
                    print(f"[{now()}] ⚠️ [API] Gói tin API trống, không chứa mảng 'products' hay 'productList'! Dữ liệu gốc chứa các Key sau: {list(body.keys())} -> data: {data_keys}")
        except Exception as e:
            pass # Ignore read errors, sometimes requests abort midway

    def extract_ssr_data(self):
        """Module A: Bóc tách SSR (Dữ liệu khối khổng lồ)"""
        print(f"[{now()}] ⛏️ Đang đào bới SSR gốc của Website...")
        try:
            content = self.page.content()
            # Tìm thẻ chứa cấu trúc hệ thống Tiktok
            match = re.search(r'<script\s+id="__MODERN_ROUTER_DATA__"[^>]*>(.*?)</script>', content, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                
                # Biểu thức JMESPath cực mạnh để chộp thẳng vào list sản phẩm (Tránh duyệt for loop cực nhọc)
                # Tuỳ theo Tiktok thay đổi mà đường dẫn có thể là query list
                # Đây là mẫu tìm kiếm chéo
                result = jmespath.search("*.queries[?state.data.product_list].state.data.product_list[]", data)
                
                if not result:
                     # Thử mẫu mới dựa trên hình ảnh người dùng chụp (categoryProductsData.productList)
                     result = jmespath.search("*.queries[?state.data.categoryProductsData].state.data.categoryProductsData.productList[]", data)
                     
                     if not result:
                         result = jmespath.search("*.queries[?state.data.products].state.data.products[]", data)
                     
                if result:
                    products = result[0] if isinstance(result[0], list) else result
                    print(f"[{now()}] 💎 [SSR] Xuất sắc! Bóc tách thành công {len(products)} sản phẩm từ Server-Side Render gốc của web.")
                    process_product_data(products, source_label="Dữ liệu SSR")
                else:
                    print(f"[{now()}] ⚠️ Không tìm thấy biến productList qua JMESPath. Đang thử quét thô bằng Regex...")
                    # Phân tích cú pháp thô bằng Regex làm fallback cuối cùng
                    try:
                         # Tìm cụm "productList":[...] trong chuỗi JSON
                         pl_match = re.search(r'"productList":\s*(\[.*?\])\s*,\s*"product_price_info"', json_str, re.DOTALL)
                         if not pl_match:
                             pl_match = re.search(r'"productList":\s*(\[.*?\])\s*}', json_str, re.DOTALL)
                             
                         if pl_match:
                             raw_list_str = pl_match.group(1)
                             products = json.loads(raw_list_str)
                             print(f"[{now()}] 🛡️ [SSR Fallback] Bóc tách thành công {len(products)} sản phẩm bằng phân tích thô Regex!")
                             process_product_data(products, source_label="Dữ liệu SSR (Regex Fallback)")
                         else:
                             print(f"[{now()}] ❌ Chịu thua! Không thể bóc tách cấu trúc SSR hiện tại của Tiktok. Phải chờ API Xem Thêm.")
                             with open("ssr_debug.json", "w", encoding="utf-8") as f:
                                 f.write(json_str)
                             print(f"[{now()}] 💾 Đã lưu cục Data dị dạng vào ssr_debug.json để phân tích sau.")
                    except Exception as ex_regex:
                         print(f"[{now()}] ❌ Lỗi khi phân tích thô SSR: {ex_regex}")
            else:
                print(f"[{now()}] ⚠️ Không tìm thấy khối <script id='__MODERN_ROUTER_DATA__'> trong HTML. Có thể trang chưa load kịp hoặc bị chặn dính Captcha ngầm.")
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi bóc tách SSR: {e}")

    def run_scraper_loop(self):
        """Module C: Vòng lặp tương tác tự động click"""
        self.start_context()
        try:
            print(f"[{now()}] 🌍 Đang truy cập: {CATEGORY_URL}")
            self.page.goto(CATEGORY_URL, timeout=60000, wait_until="networkidle")
            
            # Kiem tra Captcha (Doi toi da 10 giay de Captcha hien ra)
            captcha_detected = False
            for _ in range(10):
                if self.page.locator("text='Verify to continue'").count() > 0 or self.page.locator("text='Xác minh để tiếp tục'").count() > 0 or self.page.locator("#captcha-verify-image").count() > 0:
                    captcha_detected = True
                    break
                time.sleep(1)
                
            if captcha_detected:
                print(f"[{now()}] ⚠️ [CẢNH BÁO] Hệ thống Tiktok dội Captcha hình ảnh!")
                
                # Thử giải tự động bằng 2Captcha tối đa 3 lần
                from Core.human_logic import PlaywrightCaptchaSolver
                solver_instance = PlaywrightCaptchaSolver(self.page)
                
                # Lấy target_id từ CATEGORY_URL
                import re
                t_id = "unknown"
                match_c = re.search(r'/c/[^/]+/(\d+)|/category/.*?(\d+)', CATEGORY_URL)
                if match_c:
                    t_id = match_c.group(1) or match_c.group(2)
                    
                captcha_context = {
                    'module_name': 'Scraping_Stage_1',
                    'worker_id': os.environ.get("WORKER_ID", "adminLuan031094"),
                    'target_type': 'category',
                    'target_id': t_id
                }
                
                captcha_cleared = False
                for attempt in range(1, 6):
                    print(f"[{now()}] 🤖 [BỐT GIẢI MÃ] Lần thử nghiệm thu {attempt}/5...")
                    solved_auto = solver_instance.solve(captcha_context)
                    time.sleep(3)
                    
                    # Kiểm tra xem Captcha đã biến mất chưa
                    if self.page.locator("text='Verify to continue'").count() == 0 and self.page.locator("text='Xác minh để tiếp tục'").count() == 0 and self.page.locator("#captcha-verify-image").count() == 0 and self.page.locator(".captcha_verify_container").count() == 0:
                        captcha_cleared = True
                        print(f"[{now()}] 🎉 BỐT GIẢI MÃ THÀNH CÔNG ở lần thử {attempt}!")
                        break
                        
                    print(f"[{now()}] ❌ Lần thử {attempt} thất bại. Đang đợi tải lại Captcha mới...")
                    time.sleep(2)
                
                if not captcha_cleared:
                    print(">>> TỰ ĐỘNG THẤT BẠI. VUI LÒNG CHUỘT VÀO TRÌNH DUYỆT VÀ KÉO MẢNH GHÉP ĐỂ MỞ KHÓA TIKTOK <<<")
                    
                    webhook_url = os.environ.get("WEBHOOK_URL")
                    if webhook_url:
                        try:
                            payload = {
                                "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                                "task_code": "STEP_1_RAW_SCRAPE",
                                "status": "captcha_required",
                                "data": {
                                    "total_discovered": total_scraped_items
                                },
                                "message": "Tiktok đòi giải Captcha! Đệ tử 2Captcha bất lực, sếp vào xử lý bằng tay nhé!"
                            }
                            import json
                            r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                            if r.status_code in [200, 201, 202, 204]:
                                print(f"[{now()}] 📲 Đã bắn Webhook cầu cứu sếp qua Zalo! (HTTP {r.status_code})")
                            else:
                                print(f"[{now()}] ⚠️ [WEBHOOK] N8N trả về lỗi: Mã {r.status_code} - Dữ liệu: {r.text}")
                        except Exception as e:
                            print(f"[{now()}] ❌ Lỗi kết nối Webhook N8N: {e}")
                            
                    # Vong lap cho den khi Captcha bien mat
                    print(f"[{now()}] ⏳ Đang chờ sếp giải Captcha bằng tay (Tối đa 5 phút)...")
                    for _ in range(300):
                        if self.page.locator("text='Verify to continue'").count() == 0 and self.page.locator("text='Xác minh để tiếp tục'").count() == 0 and self.page.locator("#captcha-verify-image").count() == 0:
                            break
                        time.sleep(1)
                        
                print(f"[{now()}] ✅ Cổng đã mở! Tiếp tục công việc cào Data...")
                time.sleep(3)
            
            # Giai đoạn 1: Móc SSR (Đợi 10s theo yêu cầu để DOM kịp Load)
            print(f"[{now()}] ⏳ Đang đợi 10 giây để toàn bộ khối hệ thống SSR của Tiktok hiển thị hoàn chỉnh...")
            time.sleep(10)
            self.extract_ssr_data()
            
            # Giai đoạn 2: Tương tác Cuộn & Click liên hoàn
            click_target = "button:has-text('View more'), button:has-text('Xem thêm'), button:has-text('Thêm kết quả')"
            
            empty_scrolls = 0
            while empty_scrolls < 10:
                # Scroll tới cuối để nút lòi ra
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)
                print(f"[{now()}] ⏬ Đang cuộn trang để tìm nội dung... (Thử thách {empty_scrolls+1}/10)")
                
                # Check for the button
                if self.page.locator(click_target).count() > 0:
                    button = self.page.locator(click_target).first
                    if button.is_visible(timeout=5000):
                        button.scroll_into_view_if_needed()
                        time.sleep(1) # Chờ animation
                        button.click()
                        self.click_count += 1
                        print(f"[{now()}] 👆 Đã phát hiện và nhấp nút 'Xem thêm'. Lần click thứ: {self.click_count}")
                        
                        # Chờ API tải mảng mới
                        time.sleep(random.uniform(2, 4)) 
                        empty_scrolls = 0 # Nút có xuất hiện -> Không tính là cuộn vòng vo
                        
                        # Cơ chế tái sinh chống rò rỉ RAM (Anti-Leak)
                        if self.click_count % 50 == 0:
                            print(f"[{now()}] ⚠️ Đạt ranh giới 50 clicks. Khởi động lại Context để xả RAM...")
                            self.close_context()
                            time.sleep(3)
                            self.start_context()
                            self.page.goto(CATEGORY_URL, timeout=60000, wait_until="networkidle") # Trở lại và lặp
                    else:
                        empty_scrolls += 1
                else:
                    empty_scrolls += 1
                    
                time.sleep(random.uniform(2, 4)) # Giả lập tương tác người
                
            print(f"[{now()}] 🛑 Không còn nút Xem thêm nào. Đã cuộn hết danh mục!")
            
            # Bắn webhook thành công khi xong
            webhook_url = os.environ.get("WEBHOOK_URL")
            if webhook_url:
                try:
                    payload = {
                        "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                        "task_code": "STEP_1_RAW_SCRAPE",
                        "status": "success",
                        "data": {
                            "total_discovered": total_scraped_items
                        },
                        "message": f"Đã cào xong {total_scraped_items} sản phẩm thô, sếp cho chạy bước 2 nhé!"
                    }
                    import json
                    r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                    print(f"[{now()}] 📲 Đã gửi Webhook tổng kết cho N8N! (HTTP {r.status_code})")
                except Exception as e:
                    print(f"[{now()}] ❌ Lỗi gửi Webhook kết thúc: {e}")

        except Exception as e:
            print(f"[{now()}] ❌ Lỗi vòng lặp quét: {e}")
            traceback.print_exc()
            
            # Webhook lỗi chung
            webhook_url = os.environ.get("WEBHOOK_URL")
            if webhook_url:
                try:
                    payload = {
                        "tiktok_account_id": os.environ.get("TIKTOK_ACCOUNT_ID"),
                        "task_code": "STEP_1_RAW_SCRAPE",
                        "status": "error",
                        "data": {
                            "total_discovered": total_scraped_items,
                            "error": str(e)
                        },
                        "message": "Có lỗi bất ngờ khi quét sản phẩm thô."
                    }
                    import json
                    requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                except:
                    pass
        finally:
            self.close_context()

if __name__ == "__main__":
    import random
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    tiktok_account_id = os.environ.get("TIKTOK_ACCOUNT_ID")
    
    if not tiktok_account_id:
        print(f"[{now()}] ❌ Thiếu biến môi trường TIKTOK_ACCOUNT_ID. Bắt buộc gọi từ Gateway hoặc truyền N8N!")
        sys.exit(1)
        
    print(f"======================================================")
    print(f"   TIKTOK CATEGORY SCRAPER - ACCOUNT ID: {tiktok_account_id}   ")
    print(f"======================================================")
    
    # Lấy thông tin từ Database Affiliate thay vì client_registry
    acc_data = tiktok_db.get_tiktok_account_by_id(tiktok_account_id)
    if not acc_data or not acc_data.get('chrome_profile_folder'):
        print(f"[{now()}] ❌ Không tìm thấy Profile Chrome trong bảng tiktok_accounts cho ID = {tiktok_account_id}.")
        sys.exit(1)
        
    folder = acc_data['chrome_profile_folder']
    profile_absolute_path = os.path.join(r"D:\ChromeAutomation\AdminScraperProfiles", folder)
    
    print(f"[{now()}] 🔍 Đã liên kết với Admin Profile: {profile_absolute_path}")
    
    scraper = TiktokScraper(profile_absolute_path)
    scraper.run_scraper_loop()
