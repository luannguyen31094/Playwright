import threading
import sys, time, os, psycopg2, ctypes, requests, shutil, psutil, signal

# Ép Python phải nhìn vào thư mục hiện tại để tìm folder Core
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from flask import Flask, request, jsonify
from waitress import serve
from Core.database_info import DB_CONFIG, get_sys_var
from Core import db_manager
from Core.js_payloads import get_morphing_js
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_PROJECT_VN_URL = "https://labs.google/fx/vi/tools/flow/project"

def get_public_ip():
    try:
        ip = requests.get('https://api.ipify.org', timeout=3).text
        print(f"🌐 IP hiện tại của dây mạng: {ip}")
        return ip
    except:
        print("🌐 IP hiện tại của dây mạng: (Lỗi Timeout hoặc Mất mạng)")
        return "Không lấy được IP"

get_public_ip()

# --- [MỚI] THAM SỐ CỐ ĐỊNH TỪ DÒNG LỆNH ---
if len(sys.argv) < 3:
    print("❌ Thieu tham so! Cu phap: python playwright_worker.py [Worker_ID] [Port]")
    sys.exit()

WORKER_ID = sys.argv[1]
PORT = int(sys.argv[2])
SHORT_ID = WORKER_ID.replace("Worker_", "W_")
USER_DATA_DIR = get_sys_var('ROOT_PATH', r'D:\ChromeAutomation')

# Biến toàn cục
app = Flask(__name__)
playwright_instance = None
browser_context = None
page = None
is_busy = False
PROFILE = None
PROJECT_ID = None
page_navigating = False

def delayed_self_destruct(delay=2):
    def kill():
        time.sleep(delay)
        print(f"[{now()}] 🧨 BÙM! Worker đã tự hủy thành công.")
        os._exit(0)
    threading.Thread(target=kill, daemon=True).start()

def now(): return time.strftime('%H:%M:%S')

def set_window_title(title):
    ctypes.windll.kernel32.SetConsoleTitleW(title)

def get_worker_config_full():
    return db_manager.get_worker_full_config(WORKER_ID)

def auto_shutdown_monitor():
    offline_counter = 0
    print(f"[{now()}] [{WORKER_ID}] 🕵️ Cảm biến tự động tắt khởi động.")
    while True:
        try:
            _, _, status, _, _, _ = get_worker_config_full()
            if status and status.lower() != 'on':
                offline_counter += 30
                rem = 60 - offline_counter
                if rem > 0:
                    print(f"[{now()}] [{WORKER_ID}] ⚠️ Trạng thái {status}. Tắt sau {rem}s...")
            else:
                if offline_counter > 0:
                    print(f"[{now()}] [{WORKER_ID}] ✨ Online trở lại. Reset.")
                offline_counter = 0
                
            if offline_counter >= 60:
                print(f"[{now()}] [{WORKER_ID}] 🛑 Offline quá 1 phút. Dừng!")
                global browser_context, playwright_instance
                if browser_context:
                    try: browser_context.close()
                    except: pass
                if playwright_instance:
                    try: playwright_instance.stop()
                    except: pass
                os._exit(0)
        except Exception as e:
             print(f"[{now()}] [MONITOR] {e}")
        time.sleep(30)

def robust_rmtree(path, max_retries=5, delay=2):
    for i in range(max_retries):
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                return True
        except:
            time.sleep(delay)
    return False

BASE_PATH = get_sys_var('ROOT_PATH', r'D:\ChromeAutomation')

def step_1_kill_process(profile_folder_name):
    full_path = os.path.join(BASE_PATH, profile_folder_name).lower()
    print(f"--- [BƯỚC 1: GIẾT] ---")
    
    global browser_context, playwright_instance, page
    if browser_context:
        try: browser_context.close()
        except: pass
    if playwright_instance:
        try: playwright_instance.stop()
        except: pass
    page = None

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'chrome' in proc.info['name'].lower() or 'chromium' in proc.info['name'].lower():
                cmd = " ".join(proc.info['cmdline']).lower()
                if full_path in cmd:
                    proc.kill()
                    print(f"[{now()}] ⚰️ Đã bắn hạ PID {proc.info['pid']}.")
        except: continue
    return True

def step_2_delete_folder(profile_folder_name):
    full_path = os.path.join(BASE_PATH, profile_folder_name)
    print(f"--- [BƯỚC 2: XÓA] ---")
    if os.path.exists(full_path):
        try:
            shutil.rmtree(full_path)
            return True
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi xóa: {e}")
            return False
    return False

def step_3_trigger_reborn():
    print(f"--- [BƯỚC 3: TÁI SINH] ---")
    print(f"[{now()}] 🚀 Phát lệnh tử hình bằng Tự Sát (Exit 42). Worker sẽ Reboot sau 2s!")
    def harakiri():
        import time, os
        time.sleep(2)  # Đợi API trả về thành công rồi tự sát
        os._exit(42)
    import threading
    threading.Thread(target=harakiri, daemon=True).start()
    return "RESTART_REQUIRED"

def handle_recaptcha_rebirth(old_profile_name):
    global browser_context, playwright_instance, page
    try:
        # User requested pure numbers. Multiplying by 1000000 (Microseconds) 
        # heavily mitigates the 15.6ms Window OS clock tick collision.
        import time, random
        # Thêm 1 tí random 2 số lót đề phòng Windows clock tick trả về chung 1 kết quả
        new_profile_name = f"Profile_{int(time.time() * 1000)}{random.randint(10,99)}"
        db_res = db_manager.handle_recaptcha_reborn_db(WORKER_ID, new_profile_name)
        
        if db_res.get("status") == "success":
            print(f"[{now()}] 🛡️ [REBIRTH] Đổi Profile -> {new_profile_name}")
            KILL_LOCK = os.path.join(USER_DATA_DIR, "global_kill.lock")
            
            if os.path.exists(KILL_LOCK):
                while os.path.exists(KILL_LOCK):
                    if time.time() - os.path.getmtime(KILL_LOCK) > 30:
                        try: os.remove(KILL_LOCK)
                        except: pass
                        break
                    time.sleep(0.5)
            try:
                with open(KILL_LOCK, "w") as f: f.write(WORKER_ID)
                step_1_kill_process(old_profile_name)
                step_2_delete_folder(old_profile_name)
                print(f"[{now()}] ✅ Xóa sạch mảnh vỡ {old_profile_name}!")
            finally:
                if os.path.exists(KILL_LOCK):
                    try: os.remove(KILL_LOCK)
                    except: pass
                    
            browser_context = None
            page = None
            playwright_instance = None
            return {
                "status": "error",
                "error_type": "RECAPTCHA_REGENERATED",
                "new_profile": new_profile_name,
                "message": f"Dính Captcha. Đã đổi sang {new_profile_name}"
            }
        else:
            if db_res.get("error_type") == "RECAPTCHA_MAX_REACHED":
                return {"status": "error", "error_type": "RECAPTCHA_MAX_REACHED", "message": "Quá giới hạn Retry."}
            return db_res
    except Exception as e:
        return {"status": "error", "message": str(e)}

def smash_google_popup(pg):
    js_nuclear = """
    function findAndClick(root) {
        const selectors = ['button', 'div[role="button"]', 'a[role="button"]'];
        for (let selector of selectors) {
            const elements = root.querySelectorAll(selector);
            for (let el of elements) {
                const text = el.innerText.toLowerCase();
                if (text.includes('without an account') || text.includes('không cần tài khoản') || text.includes('not now') || text.includes('để sau') || text.includes('no thanks') || text.includes('không, cảm ơn')) {
                    el.click();
                    return true;
                }
            }
        }
        const allElements = root.querySelectorAll('*');
        for (let el of allElements) {
            if (el.shadowRoot) {
                if (findAndClick(el.shadowRoot)) return true;
            }
        }
        return false;
    }
    return findAndClick(document);
    """
    try:
        pg.keyboard.press("Escape")
        return pg.evaluate(js_nuclear)
    except: return False

def check_and_login_google(pg, email, password):
    print(f"[{now()}] 🔑 [AUTO-LOGIN] Đang nạp account: {email}")
    try:
        # Nhập Email
        email_box = pg.locator('input[type="email"]').first
        if email_box.is_visible(timeout=5000):
            email_box.fill(email)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(4000)
            
        # Nhập Password
        pass_box = pg.locator('input[type="password"][name="Passwd"], input[type="password"]').first
        if pass_box.is_visible(timeout=15000):
            pass_box.click()
            pg.keyboard.type(password, delay=50)
            pg.wait_for_timeout(1000)
            pg.keyboard.press("Enter")
            print(f"[{now()}] ✅ Nạp mật khẩu xong. Đợi 10s...")
            pg.wait_for_timeout(10000)
            return True
        return False
    except Exception as e:
        print(f"[{now()}] ❌ [LOGIN_ERROR] {e}")
        return False

def handle_google_login_flow(pg, email, password):
    print(f"[{now()}] 📡 Đang Radar Playwright Project UI (Trần 60s)...")
    for i in range(60):
        # THÀNH CÔNG: Ô nhập prompt hện lên -> Xong! (Vững hơn kỹ thuật soi API Network cũ)
        try:
            prompt_box = pg.locator('div[role="textbox"][data-slate-editor="true"], textarea').first
            if prompt_box.is_visible(timeout=500):
                print(f"[{now()}] 🎯 PHÁT HIỆN GIAO DIỆN PROJECT! Đã qua vòng Login.")
                return "SUCCESS"
        except: pass
            
        curr_url = pg.url
        try:
            create_btn = pg.locator("button:has-text('Create with Flow')").first
            if create_btn.is_visible(timeout=500):
                print(f"[{now()}] 👆 Phát hiện màn hình chờ, đang bấm 'Create with Flow'...")
                create_btn.click()
                pg.wait_for_timeout(3000)
                continue
        except: pass
            
        try:
            if "accounts.google.com" in curr_url or pg.locator('input[type="email"]').is_visible(timeout=500):
                check_and_login_google(pg, email, password)
            else:
                smash_google_popup(pg)
        except: pass
            
        if i == 20 or i == 40:
            print(f"[{now()}] 🔃 Kẹt quá lâu, Không thấy giao diện! Tiến hành F5 tải lại trang...")
            try: pg.reload(wait_until="commit")
            except: pass
            
        time.sleep(1)
        
    print(f"[{now()}] 🛑 Hết 60s chờ UI khởi động. Hủy!")
    return "FAILED"

def init_browser():
    global playwright_instance, browser_context, page, PROFILE, PROJECT_ID
    
    if page:
        try:
            pg_title = page.title()
            print(f"[{now()}] ✅ Trình duyệt sống dai.")
        except Exception:
            print(f"[{now()}] ⚡ Xác chết. Giết để hồi sinh.")
            step_1_kill_process(PROFILE)
            page = None

    folder, proj, status, email, password, acc_status = get_worker_config_full()
    if status and status.lower() != 'on':
        step_1_kill_process(folder)
        return
        
    if page is None:
        PROFILE = folder
        PROJECT_ID = proj
        if not PROFILE or not PROJECT_ID:
            print(f"❌ Worker {WORKER_ID} chưa cấu hình đủ.")
            return
            
        print(f"[{now()}] Khởi tạo Playwright cho {PROFILE}...")
        playwright_instance = sync_playwright().start()
        user_data_path = os.path.join(USER_DATA_DIR, PROFILE)
        
        # 📏 Tính toán vị trí xếp hạng rào ô (Ma trận 2 Cột) để TUYỆT ĐỐI không đè mép
        width = 450
        height = 250
        index = (PORT % 10) - 1 
        
        # Chia 2 Cột: index 0,1,2 -> Cột 0; index 3,4,5 -> Cột 1
        col = index // 3
        row = index % 3
        
        # Chromium mặc định từ chối thu nhỏ cửa sổ nhỏ hơn 800x600, nên ép cứng khoảng cách x,y siêu bự
        x_pos = col * 820
        y_pos = row * 620
        
        browser_context = playwright_instance.chromium.launch_persistent_context(
            user_data_path,
            headless=False,
            viewport={'width': 800, 'height': 600},
            args=[
                f"--window-position={int(x_pos)},{int(y_pos)}",
                f"--window-size={width},{height}",
                "--force-device-scale-factor=0.5", # Nhồi 800x600 vào cửa sổ bé tí
                
                # Cờ chống mờ + Occlusion (kế thừa Selenium)
                "--disable-features=CalculateNativeWinOcclusion",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ],
            ignore_default_args=["--enable-automation"]
        )
        
        # Lấy trang đầu tiên và hủy diệt BÀN THẠCH rác khôi phục từ luồng Crash
        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        for i, p in enumerate(browser_context.pages):
            if p != page:
                try: p.close()
                except: pass
        
        # Bắt toàn bộ quá trình bơm Payload JS để lôi cổ lỗi 403 Safety Filter ra ánh sáng
        def handle_console(msg):
            txt = msg.text
            if "[SaaS-Worker]" in txt or "LỖI 403" in txt or "CAMa" in txt:
                print(f"[{now()}] 🧠 {txt}")
        page.on("console", handle_console)
        
        page.set_default_timeout(60000)

    # 3. Radar
    if "labs.google" not in page.url:
        page.goto(f"{BASE_PROJECT_VN_URL}/{PROJECT_ID}", wait_until="commit")

    status = handle_google_login_flow(page, email, password)
    if status == "SUCCESS":
        print(f"[{now()}] ✅ ONLINE Playwright!")
        set_window_title(f"[ {SHORT_ID} ] - 🟢 ONLINE Pw - {PROFILE}")
        try:
            page.reload(wait_until="commit")
            pg_title = page.title()
        except: pass
        return True
    else:
        print(f"[{now()}] ⚠️ Lỗi khởi tạo Login.")
        return False

@app.route('/status', methods=['GET'])
def get_status():
    try: url = page.url if page else "None"
    except: url = "Hanging"
    return jsonify({
        "status": "online", "is_busy": is_busy,
        "worker_id": WORKER_ID, "profile": PROFILE,
        "project_id": PROJECT_ID, "current_url": url
    })

@app.route('/execute', methods=['POST'])
def execute():
    global is_busy, page, PROJECT_ID, PROFILE
    if is_busy: return jsonify({"status": "error", "message": "Busy"}), 503
    
    is_busy = True
    data = request.json
    task_type = data.get('task_type') or data.get('type') or 'image_gen'
    
    try:
        folder, proj, _, _, _, _ = get_worker_config_full()
        if folder: 
            PROFILE = folder
            PROJECT_ID = proj

        if task_type != "video_check" or page is None:
            if init_browser() == False:
                is_busy = False
                return jsonify({"status": "error", "message": "UI Radar Timeout. Page is stuck.", "code": "TIMEOUT_RETRY"}), 408

        if page is None:
            return jsonify({"status": "error", "message": "Browser init failed"}), 500

        if task_type == "test403":
            print(f"\n[{now()}] 🛡️ [TEST403] Tái sinh {PROFILE}")
            is_busy = False
            res = handle_recaptcha_rebirth(PROFILE)
            if res.get("status") == "success" or res.get("error_type") == "RECAPTCHA_REGENERATED":
                step_3_trigger_reborn()
            return jsonify(res)

        endpoint = data.get('endpoint')
        
        # 1. Thử lấy payload từ N8N (Backward Compatibility)
        payload = data.get('payload') or data.get('requests') or data.get('imageInput')
        
        # 2. Kích hoạt Database-Driven Payload (Mô hình Mới)
        if not payload and endpoint:
            template = db_manager.get_api_payload_template(endpoint)
            if template:
                payload = template
                # Bơm miếng thịt Base64 từ lõi N8N vào Xương Khung DB
                if data.get('rawImageBytes'):
                    payload['imageBytes'] = data.get('rawImageBytes')

        if not payload: return jsonify({"status": "error", "message": "Empty Payload and missing DB Template"}), 400

        script = get_morphing_js(task_type, endpoint, payload, PROJECT_ID)
        
        # Chuyển Playwright Evaluate Promise
        evaluate_script = f"""
        async () => {{
            return await new Promise((resolve) => {{
                // Intercept callback argument để trả về Python
                const arguments = [resolve];
                {script}
            }});
        }}
        """

        print(f"[{now()}] [{PROFILE}] 📩 Pw Evaluate: [{task_type.upper()}] (Trần 150s)")
        
        try:
            # Cơ chế làm sạch: refresh trước mỗi lệnh để xóa rác React DOM bị kẹt từ Cache cũ
            if page and task_type not in ["test403"]:
                print(f"[{now()}] 🧹 [DOM CLEANER] Tải lại trang (F5) trước tải trọng mới để xóa rác React cũ...")
                try: page.reload(wait_until="commit")
                except: pass
                
                try:
                    page.wait_for_timeout(4000) # Đợi React nạp DOM sau khi F5 (Tăng lên 4s để chống Black Screen UI)
                    tb = page.locator('div[role="textbox"][data-slate-editor="true"], textarea').first
                    if tb.is_visible(timeout=8000):
                        # Gán thẳng payload vạn năng (dù là Init hay Prompt Thật)
                        actual_prompt = payload.get("prompt", f"Init-{int(time.time())}") + " "
                        
                        # Copy Prompt vào Clipboard (Khay nhớ tạm của Hệ điều hành)
                        page.evaluate("prompt_text => navigator.clipboard.writeText(prompt_text)", actual_prompt)
                        
                        tb.click()
                        # Tổ hợp phím quét khối và dán OS-level cực sạch (Không bao giờ lỗi Select All)
                        page.keyboard.press("Control+a")
                        page.keyboard.press("Backspace")
                        page.keyboard.press("Control+v")
                        page.keyboard.press("Space")
                        
                        page.wait_for_timeout(2000) # Cho SlateJS nhận diện OnChange Input
                except: pass

            # Tăng timeout lúc execute JS
            page.set_default_timeout(150000)
            result = page.evaluate(evaluate_script)
            page.set_default_timeout(60000)
        except PlaywrightTimeoutError:
            print(f"[{now()}] ⏳ Timeout đánh giá JS!")
            return jsonify({"status": "error", "message": f"Worker Timeout", "code": "TIMEOUT_RETRY"}), 408

        res_str = str(result).lower()
        
        # Tách bạch Cảnh báo Ban Account rành mạch, không mix với Lỗi Trạng thái Video (FAILED)
        banned_keywords = ["recaptcha", "permission_denied", "filtered"]
            
        if any(kw in res_str for kw in banned_keywords):
            print(f"[{now()}] 🚨 Phát hiện dấu hiệu Bị Chặn/Lọc (Filter/Recaptcha). Kích hoạt Hồi Sinh!")
            res = handle_recaptcha_rebirth(PROFILE)
            if res.get("status") == "success" or res.get("error_type") == "RECAPTCHA_REGENERATED":
                step_3_trigger_reborn()
            return jsonify(res)

        db_manager.reset_worker_retry(WORKER_ID)
        
        if isinstance(result, dict) and result.get("status") == "error":
            print(f"[{now()}] ❌ Lỗi JS: {result.get('message')}")
            return jsonify({"status": "error", "message": result.get("message"), "worker_id": WORKER_ID, "details": result}), 400
            
        print(f"[{now()}] ✅ Xong task!")
        return jsonify({"status": "success", "worker_id": WORKER_ID, "message": result})
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"[{now()}] ❌ Lỗi PW: {error_msg}")
        if "timeout" in error_msg:
            return jsonify({"status": "error", "message": "Timeout", "code": "TIMEOUT_RETRY"}), 408
        if any(kd in error_msg for kd in ["429", "exhausted", "quota", "limit"]):
            return jsonify({"status": "error", "message": "Sạch Quota", "code": "QUOTA_STOP"}), 429
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        is_busy = False

if __name__ == '__main__':
    def force_die(sig, frame):
        os._exit(0)
    try:
        signal.signal(signal.SIGINT, force_die)
        signal.signal(signal.SIGTERM, force_die)
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, force_die)
    except: pass

    set_window_title(f"[ {SHORT_ID} ] - PW:{PORT} - 💤 CHỜ CẤU HÌNH...")
    print(f"\n{'='*60}")
    print(f"🚀 PW WORKER V9.0 READY: {WORKER_ID} | PORT: {PORT}")
    print(f"{'='*60}\n")
    threading.Thread(target=auto_shutdown_monitor, daemon=True).start()
    init_browser()
    
    # Loại bỏ Waitress Đa luồng vì con kiến trúc Playwright CẤM gọi chéo luồng!
    # Selenium cũ gọi chéo luồng được, nhưng Playwright thì ném Exception -> Chết Browser.
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) # Tắt rác log
    
    # Ép Flask chạy đinh 1 luồng duy nhất (Cùng luồng Main với Playwright)
    print(f"[{now()}] 🛡️ Kích hoạt lõi HTTP Đơn Luồng (Thread-Safe)...")
    app.run(host='0.0.0.0', port=PORT, threaded=False)
