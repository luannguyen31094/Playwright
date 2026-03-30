import os, time, requests, psycopg2, threading, json, subprocess
from flask import Flask, request, jsonify, Response, stream_with_context
from waitress import serve
from Core.database_info import get_sys_var, get_db_connection
from Core import db_manager, dispatcher

app = Flask(__name__)

def now(): return time.strftime('%H:%M:%S')
# Admin key: đặt ADMIN_KEY trong biến môi trường (production), tránh hardcode
ADMIN_KEY = os.environ.get("ADMIN_KEY", "adminLuan031094")
DEFAULT_WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://thorough-macaw-thankfully.ngrok-free.app/webhook/n8n-callback")
ROOT_PATH = get_sys_var('ROOT_PATH', r'D:\ChromeAutomation')
STATUS_WAITING = 1
STATUS_PROCESSING = 2
STATUS_TICKET_DONE = 3
STATUS_CHECKING = 4
STATUS_COMPLETED = 5
STATUS_FAILED = 6

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def _safe_filename(name):
    """Chặn path traversal: chỉ cho phép tên file an toàn (basename, không có ..)."""
    if not name or ".." in name or (os.path.sep in name and os.path.sep != "/"):
        return None
    return os.path.basename(name.replace("\\", "/"))

@app.before_request
def log_incoming_request():
    try:
        ip = get_client_ip()
        print(f"[{now()}] [MẮT THẦN] 👁️ IP: {ip} -> Đang gọi: {request.path} [{request.method}]", flush=True)
    except Exception as e: print(f"[{now()}] [LỖI LOG IP] {str(e)}", flush=True)

def process_logic(task_type, timeout=300):
    data = request.json
    key_id = data.get('key_id', '').strip()
    customer_ip = get_client_ip()

    # 1. QUYỀN ADMIN (Sếp Luân): Phân tuyến tĩnh
    if key_id == ADMIN_KEY:
        if task_type == "custom_media": base_url = "http://localhost:9001"
        elif task_type.startswith("media"): base_url = "http://localhost:9000"
        else: base_url = "http://localhost:5999"
        
        target_url = dispatcher.get_target_url(base_url, task_type)
        print(f"[{now()}] [👑 ADMIN] Tuyến đường: {task_type} -> {target_url}")
        if not target_url: return jsonify({"error": "Route không hợp lệ"}), 400
        return dispatcher.forward_request(target_url, data, timeout=600 if "custom" in task_type else timeout)

    # 2. XỬ LÝ CHO WORKER THƯỜNG: Phân tuyến động qua DB
    if not key_id: return jsonify({"status": "error", "message": "Thiếu Key ID"}), 400

    row = db_manager.get_worker_info(key_id)
    if not row:
        target_url = "http://localhost:5002/execute"
    else:
        db_port, allowed_ips, status = row
        if status and status.lower() != 'on': return jsonify({"status": "error", "message": "Worker Offline"}), 403

        # Quản lý IP qua lớp DB
        allowed_ips = allowed_ips if allowed_ips else []
        if customer_ip not in allowed_ips:
            if len(allowed_ips) >= 3: return jsonify({"status": "error", "message": "Giới hạn 3 IP"}), 403
            allowed_ips.append(customer_ip)
            db_manager.update_worker_ips(key_id, allowed_ips)

        target_url = dispatcher.get_target_url(f"http://localhost:{db_port}", task_type)
    return dispatcher.forward_request(target_url, data, timeout)    

@app.route('/api/generate', methods=['POST'])
def handle_generate():
    return process_logic(task_type="selenium", timeout=300)

@app.route('/api/merge', methods=['POST'])
def handle_merge():
    return process_logic(task_type="media", timeout=300)

@app.route('/api/edit', methods=['POST'])
def handle_edit():
    return process_logic(task_type="media_edit", timeout=150)

@app.route('/api/custom_media', methods=['POST'])
def handle_custom_media():
    # Điều hướng sang pipeline tổng hợp
    return process_logic(task_type="custom_media", timeout=600)        

@app.route('/api/messages', methods=['POST'])
def handle_openclaw_messages():
    """Nhận lệnh từ n8n và truyền cho OpenClaw chạy ngầm (Hỗ trợ Self-Healing)"""
    data = request.json or {}
    msg = data.get('message', '')
    target = data.get('agentId', 'main')
    
    if not msg:
        return jsonify({"error": "Thiếu nội dung message"}), 400
        
    print(f"\n🚀 [GATEWAY] MẮT THẦN N8N -> Kích hoạt OpenClaw: {msg[:50]}...")
    
    def trigger_openclaw():
        # Đợi 1 giây để trả kết quả 200 OK cho n8n an toàn rồi mới đánh thức OpenClaw
        time.sleep(1)
        print(f"\n[🔄 ĐANG XỬ LÝ] Đang đẩy lệnh xuống OpenClaw Native (Window Host)...")
        cmd = [
            r"C:\Users\Admin\AppData\Roaming\npm\openclaw.cmd", "agent",
            "--agent", target,
            "--message", msg
        ]
        
        import os
        custom_env = os.environ.copy()
        custom_env["OPENCLAW_OLLAMA_API_KEY"] = "ollama"
        custom_env["OPENCLAW_OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
        custom_env["OLLAMA_API_KEY"] = "ollama"
        custom_env["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=custom_env, encoding='utf-8')
            print(f"✅ [THÀNH CÔNG] OpenClaw Đã Nhận Lệnh:\n{result.stdout}\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ [LỖI NATIVE] OpenClaw chạy thất bại:\nLỗi: {e.stderr}\nOuput: {e.stdout}")
        except Exception as e:
            print(f"❌ [LỖI HỆ THỐNG] Không gọi được OpenClaw: {e}")

    # Chạy lệnh ngầm bằng Threading
    threading.Thread(target=trigger_openclaw).start()
    
    return jsonify({"status": "success", "message": "Đã phát lệnh cho OpenClaw chạy nền"}), 200
# --- [PHẦN 2: ROUTE DOWNLOAD - ĐÃ FIX 404 CHO ADMIN] ---
@app.route('/download/<path:filename>', methods=['GET'])
@app.route('/download_final/<path:filename>', methods=['GET'])
def handle_download_proxy(filename):
    safe_name = _safe_filename(filename)
    if not safe_name:
        return jsonify({"error": "Tên file không hợp lệ"}), 400
    key_id = request.args.get('key_id', '').strip()
    customer_ip = get_client_ip()
    print(f"\n🚀 [GATEWAY 8000] ĐANG XỬ LÝ: {safe_name} | 🌐 IP: {customer_ip}")

    # 1. Xác thực (Lớp DB lo)
    target_port = 9000
    if key_id != ADMIN_KEY:
        if not key_id: return jsonify({"error": "Thiếu Key"}), 401
        res = db_manager.get_worker_download_info(key_id)
        if not res: return jsonify({"error": "Key không tồn tại"}), 404
        target_port, allowed_ips = res
        if customer_ip not in (allowed_ips or []): return jsonify({"error": "IP chặn"}), 403

    # 2. Forward (Lớp Dispatcher lo)
    target_url = f"http://localhost:{target_port}/download/{safe_name}"
    print(f"📡 [FORWARD] Đang lấy hàng từ: {target_url}")
    
    response, code = dispatcher.proxy_file_download(target_url, safe_name)
    if code != 200:
        print(f"❌ LỖI SERVICE: {code}")
        return jsonify({"error": "Service lỗi"}), code
    return response

@app.route('/get_file_size/<path:filename>', methods=['GET'])
def get_file_size_variations(filename):
    safe_name = _safe_filename(filename)
    if not safe_name:
        return jsonify({"error": "Tên file không hợp lệ"}), 400
    key_id = request.args.get('key_id', '').strip()
    if key_id != ADMIN_KEY: return jsonify({"error": "Key sai"}), 401

    target_url = f"http://localhost:9000/download/{safe_name}"
    print(f"🔍 [GATEWAY 8000] Đang đo size file tại: {target_url}")
    
    true_size = dispatcher.get_remote_file_size(target_url)
    if true_size is None:
        return jsonify({"error": "File không tồn tại"}), 404
    
    variations = dispatcher.create_size_variations(safe_name, true_size)
    print(f"✅ Đã tạo xong 10 bộ lệnh bài cho file: {safe_name}")
    return jsonify(variations)
def run_sync_videos_bg():
    import sys
    print(f"[{now()}] 🔄 Bắt đầu luồng đồng bộ Video kiểm duyệt (AI)...", flush=True)
    try:
        from Tools.VideoChecker.sync_ready_videos import sync_and_organize_videos
        sync_and_organize_videos()
        print(f"[{now()}] ✅ Hoàn tất kiểm duyệt và đồng bộ AI!", flush=True)
    except Exception as e:
        print(f"[{now()}] ❌ Lỗi kiểm duyệt chạy nền: {e}", flush=True)

@app.route('/api/sync_ready_videos', methods=['GET', 'POST'])
def api_sync_ready_videos():
    try:
        threading.Thread(target=run_sync_videos_bg).start()
        print(f"[{now()}] ✅ Đã ghi nhận lệnh Sync Video AI. Luồng đang chạy nền", flush=True)
        return jsonify({"status": "accepted", "message": "Đã ghi nhận lệnh Sync Video AI. Đang chạy nền."}), 202
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi: {e}"}), 500

@app.route('/api/get_image', methods=['GET'])
def proxy_get_image():
    """Proxy nội bộ để lấy binary hình ảnh từ Media Worker (Port 9000)"""
    product_id = request.args.get('id')
    raw = request.args.get('raw', 'false') # Nếu raw=true thì bắt original, không thì lấy cropped
    
    if not product_id:
        return jsonify({"error": "Thiếu tham số id"}), 400
        
    target_url = f"http://localhost:9000/api/get_image?id={product_id}&raw={raw}"
    print(f"📡 [GATEWAY 8000] Forward lấy hình ảnh: {target_url}")
    try:
        import requests
        from flask import Response
        resp = requests.get(target_url, timeout=30)
        return Response(
            resp.content, 
            status=resp.status_code, 
            content_type=resp.headers.get('content-type', 'image/jpeg')
        )
    except Exception as e:
        print(f"❌ [LỖI] proxy_get_image cho N8N: {e}")
        return jsonify({"error": "Lỗi kết nối tới Media Worker 9000"}), 500


# --- LOGIC MỚI: ĐIỀU PHỐI VEO3 ASYNC ---
# --- [LOGIC XỬ LÝ SHOT RIÊNG BIỆT] ---
@app.route('/api/veo3/batch', methods=['POST'])
def handle_veo3_batch():
    data = request.json
    batch_id = data.get('batch_id')
    project_id = data.get('project_id')
    
    prepared_shots = []
    for shot in data.get('shots', []):
        # 1. Nhờ Kế toán ghi danh sách vào DB
        shot['db_id'] = db_manager.insert_initial_task(batch_id, project_id, shot)
        prepared_shots.append(shot)

    # 2. Nhờ Điều phối viên bắn lệnh ngầm (Async)
    threading.Thread(target=dispatcher.async_batch_processor, args=(batch_id, prepared_shots)).start()
    
    return jsonify({"status": "accepted", "batch_id": batch_id}), 202

@app.route('/api/veo3/batch_check', methods=['POST'])
def handle_veo3_batch_check():
    batch_id = request.json.get('batch_id')
    
    # 1. Lấy dữ liệu và đánh dấu DB (Kế toán làm)
    rows = db_manager.get_tasks_to_check(batch_id)
    print(f"[{now()}] 🔍 BATCH CHECK nhận Lệnh từ N8N (Batch: {batch_id}) -> Quét DB thấy {len(rows) if rows else 0} task hợp lệ (status=3).", flush=True)
    if not rows: return jsonify({"status": "no_tasks"}), 200
    
    db_manager.set_tasks_checking([row[0] for row in rows])

    # 2. Gôm nhóm (Logic tại Gateway để phân phối)
    worker_map = {}
    for _, w_id, t_id, s_idx in rows:
        if w_id not in worker_map: worker_map[w_id] = {"ops": [], "idxs": []}
        worker_map[w_id]["ops"].append({"name": t_id})
        worker_map[w_id]["idxs"].append(str(s_idx))

    # 3. Ra lệnh kiểm tra song song (Điều phối viên làm)
    threading.Thread(target=dispatcher.start_batch_check, args=(worker_map,)).start()
    
    return jsonify({"status": "checking", "total": len(rows)}), 202

@app.route('/api/veo3/batch_finalize', methods=['POST'])
def handle_veo3_batch_finalize():
    project_id = request.json.get('project_id')
    
    # 1. Lấy TẤT CẢ các task có status_id IN (3, 4) thuộc DỰ ÁN
    rows = db_manager.get_stranded_tasks_by_project(project_id)
    print(f"[{now()}] 🧹 BATCH FINALIZE càn quét Dự án: {project_id} -> Gom được {len(rows) if rows else 0} task kẹt.", flush=True)
    if not rows: return jsonify({"status": "no_tasks", "message": "Không có task bị kẹt"}), 200
    
    db_manager.set_tasks_status([row[0] for row in rows], 4, "Đang chốt sổ (Finalize)...")

    # 2. Gôm nhóm (Logic tại Gateway để phân phối)
    worker_map = {}
    for _, w_id, t_id, s_idx in rows:
        if w_id not in worker_map: worker_map[w_id] = {"ops": [], "idxs": []}
        worker_map[w_id]["ops"].append({"name": t_id})
        worker_map[w_id]["idxs"].append(str(s_idx))

    # 3. Bắn tín hiệu Finalize đi kèm. Dispatcher sẽ tự chia tải vòng lặp
    threading.Thread(target=dispatcher.start_batch_check, args=(worker_map, True)).start()
    
    return jsonify({"status": "finalizing", "project_id": project_id, "total": len(rows)}), 202

@app.route('/api/test_parallel', methods=['POST'])
def test_parallel():
    data = request.json
    worker_id = data.get('worker_id', 'Unknown')
    seconds = data.get('seconds', 5) # Mặc định chờ 5 giây
    
    start_time = time.strftime('%H:%M:%S')
    print(f"🕒 [{start_time}] Worker {worker_id} bắt đầu 'vít ga' trong {seconds} giây...")
    
    # Giả lập xử lý tác vụ nặng (như render video hoặc login)
    time.sleep(seconds)
    
    end_time = time.strftime('%H:%M:%S')
    print(f"✅ [{end_time}] Worker {worker_id} đã hoàn thành!")
    
    return jsonify({
        "status": "success",
        "worker_id": worker_id,
        "start": start_time,
        "end": end_time
    })

def run_tiktok_scraper_bg(category_url, tiktok_account_id, webhook_url=None):
    import sys
    print(f"[{now()}] 🕷️ Bắt đầu luồng cào dữ liệu Tiktok chạy ngầm (Account ID: {tiktok_account_id})...", flush=True)
    try:
        # Truyền Env lúc dùng subprocess
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        if category_url:
            env["CATEGORY_URL"] = category_url
        if webhook_url:
            env["WEBHOOK_URL"] = webhook_url
        if tiktok_account_id:
            env["TIKTOK_ACCOUNT_ID"] = str(tiktok_account_id)
        
        project_root = os.path.dirname(os.path.abspath(__file__))
        
        # Chạy Giai đoạn 1 (Thu thập thô)
        print(f"[{now()}] 🕷️ -> Giai đoạn 1: Category Scraper (Admin)", flush=True)
        subprocess.run(
            ["python", os.path.join("Tools", "TiktokScraper", "category_scraper_admin.py")],
            cwd=project_root,
            env=env,
            shell=True
        )
        
        # Chạy Giai đoạn 2 (Chi tiết)
        # print(f"[{now()}] 🕷️ -> Giai đoạn 2: Detail Scraper (Worker_01)", flush=True)
        # env["WORKER_ID"] = "Worker_01"
        # subprocess.run(
        #     ["python", os.path.join("Tools", "TiktokScraper", "detail_scraper_worker.py")],
        #     cwd=project_root,
        #     env=env,
        #     shell=True
        # )
        print(f"[{now()}] ✅ Hoàn tất toàn bộ chu trình cào dữ liệu Tiktok!", flush=True)
    except Exception as e:
        print(f"[{now()}] ❌ Lỗi hệ thống cào Tiktok: {e}", flush=True)

def run_showcase_sync_bg(tiktok_account_id, webhook_url=None):
    import sys
    print(f"[{now()}] 🔄 Bắt đầu luồng đồng bộ Showcase chạy ngầm (Account ID: {tiktok_account_id})...", flush=True)
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        if webhook_url:
            env["WEBHOOK_URL"] = webhook_url
        if tiktok_account_id:
            env["TIKTOK_ACCOUNT_ID"] = str(tiktok_account_id)
        
        project_root = os.path.dirname(os.path.abspath(__file__))
        
        print(f"[{now()}] 🔄 -> Chạy Web Affiliate Validator (Playwright)", flush=True)
        subprocess.run(
            ["python", os.path.join("Tools", "TiktokScraper", "web_affiliate_validator.py")],
            cwd=project_root,
            env=env,
            shell=True
        )
        print(f"[{now()}] ✅ Hoàn tất đồng bộ Showcase!", flush=True)
    except Exception as e:
        print(f"[{now()}] ❌ Lỗi đồng bộ Showcase: {e}", flush=True)

def run_commission_check_bg(tiktok_account_id, webhook_url=None):
    import sys
    print(f"[{now()}] 💰 Bắt đầu luồng kiểm tra Hoa hồng chạy ngầm (Account ID: {tiktok_account_id})...", flush=True)
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        if webhook_url:
            env["WEBHOOK_URL"] = webhook_url
        if tiktok_account_id:
            env["TIKTOK_ACCOUNT_ID"] = str(tiktok_account_id)
        
        project_root = os.path.dirname(os.path.abspath(__file__))
        
        print(f"[{now()}] 💰 -> Chạy Web Affiliate Validator (Playwright) - CHECK COMMISSION", flush=True)
        subprocess.run(
            ["python", os.path.join("Tools", "TiktokScraper", "web_affiliate_validator.py"), "check_commission"],
            cwd=project_root,
            env=env,
            shell=True
        )
        print(f"[{now()}] ✅ Hoàn tất kiểm tra Hoa hồng!", flush=True)
    except Exception as e:
        print(f"[{now()}] ❌ Lỗi kiểm tra Hoa hồng: {e}", flush=True)

def run_add_showcase_bg(tiktok_account_id, webhook_url=None):
    import sys
    print(f"[{now()}] 🛒 Bắt đầu luồng Thêm sản phẩm vào Showcase và Tạo Campaign (Account ID: {tiktok_account_id})...", flush=True)
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        if webhook_url:
            env["WEBHOOK_URL"] = webhook_url
        if tiktok_account_id:
            env["TIKTOK_ACCOUNT_ID"] = str(tiktok_account_id)
        
        project_root = os.path.dirname(os.path.abspath(__file__))
        
        print(f"[{now()}] 🛒 -> Chạy Web Affiliate Validator (Playwright) - ADD MODE", flush=True)
        subprocess.run(
            ["python", os.path.join("Tools", "TiktokScraper", "web_affiliate_validator.py"), "add_showcase"],
            cwd=project_root,
            env=env,
            shell=True
        )
        print(f"[{now()}] ✅ Hoàn tất xử lý Bước 5!", flush=True)
    except Exception as e:
        print(f"[{now()}] ❌ Lỗi khi chạy Bước 5: {e}", flush=True)

def run_process_media_bg(tiktok_account_id, tiktok_product_id=None, webhook_url=None):
    import sys
    print(f"[{now()}] 🎞️ Bắt đầu luồng Tải Media & Crop (FFMPEG) (Account ID: {tiktok_account_id})...", flush=True)
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        if webhook_url:
            env["WEBHOOK_URL"] = webhook_url
        if tiktok_account_id:
            env["TIKTOK_ACCOUNT_ID"] = str(tiktok_account_id)
            
        project_root = os.path.dirname(os.path.abspath(__file__))
        
        cmd = ["python", os.path.join("Tools", "TiktokScraper", "media_downloader.py")]
        if tiktok_product_id:
            cmd.append(str(tiktok_product_id))
            
        print(f"[{now()}] 🎞️ -> Chạy Media Downloader", flush=True)
        subprocess.run(cmd, cwd=project_root, env=env, shell=True)
        print(f"[{now()}] ✅ Hoàn tất luồng Media!", flush=True)
    except Exception as e:
        print(f"[{now()}] ❌ Lỗi khi chạy luồng Media: {e}", flush=True)

@app.route('/api/tiktok_scrape', methods=['POST'])
def trigger_tiktok_scrape():
    """Endpoint để N8N Request qua HTTP (Host: 8000)"""
    data = request.json or {}
    tiktok_account_id = data.get('tiktok_account_id')
    
    if not tiktok_account_id:
        return jsonify({"error": "Thiếu tham số tiktok_account_id. Vui lòng truyền tiktok_account_id từ N8N!"}), 400
        
    category_url = data.get('category_url')
    webhook_url = data.get('webhook_url') or DEFAULT_WEBHOOK_URL
    
    # Bắn luồng chạy ngầm để Gateway không bị kẹt (trả HTTP 202 ngay lặp tức)
    threading.Thread(target=run_tiktok_scraper_bg, args=(category_url, tiktok_account_id, webhook_url)).start()
    print(f"[{now()}] ✅ Đã ghi nhận lệnh. Luồng cào dữ liệu Tiktok đang chạy nền với ACC ID: {tiktok_account_id}", flush=True)
    return jsonify({
        "status": "accepted", 
        "message": f"Đã ghi nhận lệnh. Luồng cào dữ liệu Tiktok đang chạy nền với ACC ID: {tiktok_account_id}."
    }), 202

@app.route('/api/showcase_sync', methods=['POST'])
def trigger_showcase_sync():
    """Endpoint để N8N Request qua HTTP (Bước 2)"""
    data = request.json or {}
    tiktok_account_id = data.get('tiktok_account_id')
    
    if not tiktok_account_id:
        return jsonify({"error": "Thiếu tham số tiktok_account_id!"}), 400
        
    webhook_url = data.get('webhook_url') or DEFAULT_WEBHOOK_URL
    
    threading.Thread(target=run_showcase_sync_bg, args=(tiktok_account_id, webhook_url)).start()
    print(f"[{now()}] ✅ Đã ghi nhận lệnh Showcase Sync. Luồng đang chạy nền với ACC ID: {tiktok_account_id}", flush=True)
    return jsonify({
        "status": "accepted", 
        "message": "Đã ghi nhận lệnh Showcase Sync."
    }), 202

@app.route('/api/commission_check', methods=['POST'])
def trigger_commission_check():
    """Endpoint để N8N Request qua HTTP (Bước 3)"""
    data = request.json or {}
    tiktok_account_id = data.get('tiktok_account_id')
    
    if not tiktok_account_id:
        return jsonify({"error": "Thiếu tham số tiktok_account_id!"}), 400
        
    webhook_url = data.get('webhook_url') or DEFAULT_WEBHOOK_URL
    
    threading.Thread(target=run_commission_check_bg, args=(tiktok_account_id, webhook_url)).start()
    print(f"[{now()}] ✅ Đã ghi nhận lệnh Commission Check. Luồng đang chạy nền với ACC ID: {tiktok_account_id}", flush=True)
    return jsonify({
        "status": "accepted", 
        "message": "Đã ghi nhận lệnh Commission Check."
    }), 202

@app.route('/api/add_showcase', methods=['POST'])
def trigger_add_showcase():
    """Endpoint để N8N Request qua HTTP (Bước 5)"""
    data = request.json or {}
    tiktok_account_id = data.get('tiktok_account_id')
    
    if not tiktok_account_id:
        return jsonify({"error": "Thiếu tham số tiktok_account_id!"}), 400
        
    webhook_url = data.get('webhook_url') or DEFAULT_WEBHOOK_URL
    
    threading.Thread(target=run_add_showcase_bg, args=(tiktok_account_id, webhook_url)).start()
    print(f"[{now()}] ✅ Đã ghi nhận lệnh Add Showcase & Campaign. Luồng đang chạy nền với ACC ID: {tiktok_account_id}", flush=True)
    return jsonify({
        "status": "accepted", 
        "message": "Đã ghi nhận lệnh Add Showcase & Campaign."
    }), 202

@app.route('/api/process_media', methods=['POST'])
def trigger_process_media():
    """Endpoint để N8N Request qua HTTP tải Media FFMPEG (Bước 6)"""
    data = request.json or {}
    tiktok_account_id = data.get('tiktok_account_id')
    
    if not tiktok_account_id:
        return jsonify({"error": "Thiếu tham số tiktok_account_id!"}), 400
        
    webhook_url = data.get('webhook_url') or DEFAULT_WEBHOOK_URL
    tiktok_product_id = data.get('tiktok_product_id')
    
    threading.Thread(target=run_process_media_bg, args=(tiktok_account_id, tiktok_product_id, webhook_url)).start()
    print(f"[{now()}] ✅ Đã ghi nhận lệnh Process Media (Bước 6). Luồng đang chạy nền với ACC ID: {tiktok_account_id}", flush=True)
    return jsonify({
        "status": "accepted", 
        "message": "Đã ghi nhận lệnh Process Media."
    }), 202

if __name__ == '__main__':
    # Fix UnicodeEncodeError on Windows CMD
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    print(f"\n{'='*60}")
    print(f"🚀 GATEWAY V8.1 - ADMIN MODE ENABLED (PORT 5000)")
    print(f"{'='*60}\n")
    serve(app, host='0.0.0.0', port=8000, threads=50)