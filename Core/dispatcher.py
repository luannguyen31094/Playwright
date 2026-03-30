import threading, time, requests, json
from Core import db_manager
from flask import Response, stream_with_context, jsonify

def now(): return time.strftime('%H:%M:%S')

# ----1. Batch Check
def run_worker_check(wid, operations, shot_indices, finalize=False):
    """Luồng gọi từng máy Worker để check video"""
    try:
        clean_wid = str(wid).replace("Worker_", "").replace("worker_", "")
        port = 5000 + int(clean_wid)
        url = f"http://localhost:{port}/execute"
        payload = {"key_id": f"Worker_{clean_wid}", "type": "video_check", "payload": {"operations": operations}}
        
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 200:
            parse_and_update(wid, resp.json(), shot_indices, finalize=finalize)
        else:
            print(f"🔥 Worker {wid} từ chối Check (Mã {resp.status_code}) - Rollback về 3!")
            status_on_fail = 6 if finalize else 3
            db_manager.set_tasks_status(shot_indices, status_on_fail, f"Worker bận lỗi {resp.status_code}")
    except Exception as e:
        print(f"🔥 Worker {wid} sập: {e} - Rollback về 3!")
        status_on_fail = 6 if finalize else 3
        db_manager.set_tasks_status(shot_indices, status_on_fail, "Connection Refused")

def parse_and_update(worker_id, response_data, shot_indices=None, finalize=False):
    """Logic bóc tách tọa độ sếp chỉ định (Hỗ trợ cả Format cũ lẫn Mới)"""
    if isinstance(response_data, str):
        try:
            response_data = json.loads(response_data)
        except Exception:
            pass
    
    if not isinstance(response_data, dict):
        response_data = {}
        
    msg = response_data.get('message', {})
    if isinstance(msg, str):
        try: msg = json.loads(msg)
        except: msg = {}
    if not isinstance(msg, dict):
        msg = {}
        
    # KÍCH HOẠT NHẬN DẠNG LỖI HOẶC TÁI SINH TỪ JAVASCRIPT ĐỂ ROLLBACK VỀ 3 CỨU NẠN
    if isinstance(msg, dict):
        is_error = msg.get('status') == 'error'
        is_rebirth = msg.get('message') == 'RECAPTCHA_REGENERATED'
        
        if is_error or is_rebirth:
            err_msg = msg.get('message', 'Lỗi JS Không Xác Định')
            print(f"[{now()}] ⚠️ Worker {worker_id} tịt ngòi hoăc Tái sinh: {err_msg} - Nhồi DB về 3!")
            if shot_indices:
                status_on_fail = 6 if finalize else 3
                db_manager.set_tasks_status(shot_indices, status_on_fail, f"Thất bại ({err_msg})" if finalize else f"Đang chờ ({err_msg})")
            return
    
    
    # FORMAT MỚI CỦA GOOGLE (Dùng mảng "media")
    if 'media' in msg:
        for m in msg.get('media', []):
            raw_ticket = m.get('name')
            if not raw_ticket: continue
            ticket_id = raw_ticket.split('_')[0]  # Lọc rác đuôi ví dụ '_upsampled' để map chuẩn vào DB
            
            try:
                gen_status = m['mediaMetadata']['mediaStatus']['mediaGenerationStatus']
            except KeyError:
                gen_status = "UNKNOWN"
                
            if gen_status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                # Thử mò URL ở khắp mọi nơi có thể do Google hay đổi
                vid_data = m.get('video', {})
                veo_url = m.get('resolved_url')
                if not veo_url: veo_url = vid_data.get('playInfo', {}).get('fifeUrl')
                if not veo_url: veo_url = vid_data.get('generatedVideo', {}).get('fifeUrl')
                if not veo_url: veo_url = vid_data.get('fifeUrl')
                if not veo_url: veo_url = json.dumps(m, ensure_ascii=False) # Lấy trọn vẹn JSON để lùng sục URL ẩn
                
                db_manager.update_task_by_ticket(ticket_id, 5, "Xong!", ticket_id, veo_url)
            elif gen_status in ["MEDIA_GENERATION_STATUS_PENDING", "MEDIA_GENERATION_STATUS_ACTIVE", "MEDIA_GENERATION_STATUS_RUNNING"]:
                if finalize:
                    db_manager.update_task_by_ticket(ticket_id, 6, "Quá thời gian xử lý (Hủy)")
                else:
                    db_manager.update_task_by_ticket(ticket_id, 3, "Đang chạy...")
            else:
                db_manager.update_task_by_ticket(ticket_id, 6, f"Thất bại: {gen_status}")
                
    # FORMAT CŨ (Dùng mảng "operations") - Fallback đề phòng
    else:
        ops_list = msg.get('operations', [])
        for op in ops_list:
            ticket_id = op.get('operation', {}).get('name')
            gen_status = op.get('status')
            if not ticket_id: continue

            if gen_status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                veo_id = op.get('mediaGenerationId')
                veo_url = op.get('operation', {}).get('metadata', {}).get('video', {}).get('fifeUrl')
                db_manager.update_task_by_ticket(ticket_id, 5, "Xong!", veo_id, veo_url)
            elif gen_status == "MEDIA_GENERATION_STATUS_ACTIVE":
                if finalize:
                    db_manager.update_task_by_ticket(ticket_id, 6, "Quá thời gian xử lý (Hủy)")
                else:
                    db_manager.update_task_by_ticket(ticket_id, 3, "Đang chạy...")
            else:
                db_manager.update_task_by_ticket(ticket_id, 6, "Thất bại")

def _run_worker_sequential(w_id, ops_list, idxs_list, finalize):
    """Xử lý rải đều request (Chunk động theo cấu hình Worker) để Worker không sập mà vẫn đạt Top Speed"""
    # 1. Đo lường sức chứa của hệ thống (Tính bằng tổng lượng Worker đang BẬT)
    active_workers = db_manager.get_active_selenium_workers()
    chunk_size = len(active_workers) if active_workers else 6
    if chunk_size < 1: chunk_size = 6
    
    print(f"[{now()}] ⚖️ Điều phối viên chia tải: Cắt mẻ tối đa {chunk_size} Tickets/Lần cho Worker {w_id}!")
    
    for i in range(0, len(ops_list), chunk_size):
        chunk_ops = ops_list[i : i + chunk_size]
        chunk_idxs = idxs_list[i : i + chunk_size]
        run_worker_check(w_id, chunk_ops, chunk_idxs, finalize=finalize)
        # Cho worker thở 3 giây giữa các đợt trả kẹt cực rát
        time.sleep(3)
        
    if finalize:
        # Nhát chém cuối cùng: Đứa nào check xong mà vẫn nằm lì ở "mác số 4: Đang chốt sổ" 
        # (Lý do: Ticket bị Google xóa rỗng / Script lỗi ngầm) thì ÉP VỀ 6 toàn bộ!
        db_manager.force_kill_stranded_tasks(idxs_list)

def start_batch_check(worker_map, finalize=False):
    """Khởi chạy các luồng song song (Mỗi worker 1 luồng, bên trong chạy tuần tự)"""
    for w_id, data in worker_map.items():
        threading.Thread(target=_run_worker_sequential, args=(w_id, data["ops"], data["idxs"], finalize)).start()

# ----- 2. BATCH VIDEO
def process_single_shot(shot, attempt=1):
    """Xử lý bắn lệnh cho 1 máy Worker"""
    db_id = shot['db_id']
    worker_id = shot['worker_id']
    shot_idx = shot['shot_index']
    
    # Lọc số của Worker ("Worker_06" -> 6) để tính toán Port
    clean_worker_id = str(worker_id).replace("Worker_", "").replace("worker_", "")
    target_url = f"http://127.0.0.1:{5000 + int(clean_worker_id)}/execute"

    start_t = now()
    if attempt > 1:
        print(f"[{start_t}] 🔄 [SHOT {shot_idx}] Đợi 25s cho Worker {worker_id} Rebirth xong rồi thử lại lần {attempt}...", flush=True)
        time.sleep(25)
        
    print(f"[{start_t}] 🚀 [SHOT {shot_idx}] Bắn lệnh tới Worker {worker_id} (Lần {attempt})...")

    try:
        db_manager.update_db_status(db_id, 2, f"🚀 Đang xử lý lúc {start_t} (Lần {attempt})")
        response = requests.post(target_url, json=shot, timeout=300)
        
        if response.status_code == 200:
            res_json = response.json()
            
            # KÍCH HOẠT TỰ CHỮA LÀNH NẾU JS TRẢ VỀ LỖI (VÍ DỤ BỊ SHADOW BAN / RECAPTCHA)
            if isinstance(res_json, dict) and res_json.get('status') == 'error':
                err_msg = res_json.get('message', 'Lỗi JS Không Xác Định')
                if attempt < 3:
                    print(f"[{now()}] ⚠️ Worker {worker_id} bị cản địa: {err_msg} -> Tự động thử lại lần {attempt+1}...")
                    return process_single_shot(shot, attempt + 1)
                else:
                    db_manager.update_db_status(db_id, 6, f"Thất bại sau 3 lần rặn: {err_msg}")
                    return

            try:
                parsed_msg = None
                # Xử lý nếu res_json là list (trường hợp n8n trả về mảng)
                if isinstance(res_json, list) and len(res_json) > 0:
                    raw_data = res_json[0].get('data', res_json[0])
                    parsed_msg = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                else:
                    parsed_msg = res_json

                # 🚀 LOGIC "VÍT GA" LINH HOẠT
                ticket = None
                
                # Format MỚI: Google trả về media object
                if 'media' in parsed_msg and len(parsed_msg['media']) > 0:
                    ticket = parsed_msg['media'][0].get('name')
                elif 'message' in parsed_msg and 'media' in parsed_msg['message'] and len(parsed_msg['message']['media']) > 0:
                    ticket = parsed_msg['message']['media'][0].get('name')
                
                # Format CŨ: Google trả về operations object
                elif 'operations' in parsed_msg and len(parsed_msg['operations']) > 0:
                    ticket = parsed_msg['operations'][0]['operation']['name']
                elif 'message' in parsed_msg and 'operations' in parsed_msg['message'] and len(parsed_msg['message']['operations']) > 0:
                    ticket = parsed_msg['message']['operations'][0]['operation']['name']

                if ticket:
                    # Lấy chính xác cái UUID "56e16318..."
                    print(f"[{now()}] ✅ [SHOT {shot_idx}] QUÁ NGON! Ticket: {ticket}")
                    db_manager.update_db_status(db_id, 3, "Lấy Ticket thành công", ticket=ticket)
                else:
                    raw_str = json.dumps(parsed_msg, ensure_ascii=False)[:200]
                    raise Exception(f"Thiếu ticket (media/operations). Data: {raw_str}")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"[{now()}] ❌ [SHOT {shot_idx}] Lỗi bóc Ticket: {str(e)}")
                if attempt < 3:
                    return process_single_shot(shot, attempt + 1)
                db_manager.update_db_status(db_id, 6, error_msg)
        else:
            print(f"[{now()}] ❌ [SHOT {shot_idx}] Worker báo lỗi {response.status_code}")
            if attempt < 3:
                return process_single_shot(shot, attempt + 1)
            db_manager.update_db_status(db_id, 6, f"Worker lỗi {response.status_code}")
    except Exception as e:
        print(f"[{now()}] ⚠️ [SHOT {shot_idx}] Connection Error: {str(e)}")
        if attempt < 3:
            return process_single_shot(shot, attempt + 1)
        db_manager.update_db_status(db_id, 6, f"Lỗi: {str(e)}")

def async_batch_processor(batch_id, shots):
    """Tổng lực xử lý Batch song song"""
    print(f"\n[{now()}] 🔥 [BATCH START] Tổng lực xử lý Batch: {batch_id}")
    threads = []
    for shot in shots:
        t = threading.Thread(target=process_single_shot, args=(shot,))
        t.start()
        threads.append(t)
        time.sleep(1.5) # Nghỉ nhẹ để Chrome không sập

    for t in threads: t.join()
    print(f"[{now()}] 🏁 [BATCH END] Hoàn thành Batch: {batch_id}\n")        

# SELENIUM
def get_target_url(base_url, task_type):
    """Xác định endpoint dựa trên loại tác vụ"""
    if task_type == "media": return f"{base_url}/merge"
    elif task_type == "media_edit": return f"{base_url}/edit"
    elif task_type == "custom_media": return f"{base_url}/custom_media"
    return f"{base_url}/execute"

def forward_request(target_url, data, timeout=150):
    """Gửi lệnh tới máy đích và giữ nguyên các dòng print của sếp"""
    try:
        print(f"[{time.strftime('%H:%M:%S')}] [FORWARD] Đang gửi lệnh tới: {target_url}")
        response = requests.post(target_url, json=data, timeout=timeout)
        return response.text, response.status_code
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Worker Offline: {target_url} - {str(e)}")
        return jsonify({"status": "error", "message": "Worker Offline hoặc quá tải"}), 502


# -----4.DOWNLOAD
def proxy_file_download(target_url, filename):
    """Hàm trung chuyển file video từ máy Worker về n8n"""
    try:
        r = requests.get(target_url, stream=True, timeout=15)
        if r.status_code != 200:
            return None, r.status_code
        
        file_size = r.headers.get('Content-Length')
        def generate():
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                yield chunk
            print(f"✅ [DONE] Đã ship xong file: {filename}")

        return Response(
            stream_with_context(generate()), 
            content_type='video/mp4',
            headers={'Content-Length': file_size} if file_size else {}
        ), 200
    except Exception as e:
        return str(e), 500

def get_remote_file_size(target_url):
    """Dùng HEAD request để lấy size file mà không tải cả video"""
    try:
        r = requests.head(target_url, timeout=5)
        return int(r.headers.get('Content-Length', 0)) if r.status_code == 200 else None
    except:
        return None

def create_size_variations(filename, true_size):
    """Tạo 10 biến thể size file cho n8n 'vít ga'"""
    potential_sizes = [
        true_size, true_size - 1, true_size + 1, 
        16209173, 16209174, 16209172, 16289173,
        true_size - 2, true_size + 2, true_size + 10
    ]
    variations = []
    for i, s in enumerate(potential_sizes):
        variations.append({
            "variant_id": i + 1,
            "filename": filename,
            "video_size": s,
            "headers": {
                "Content-Type": "video/mp4",
                "Content-Length": str(s),
                "Content-Range": f"bytes 0-{s-1}/{s}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
            }
        })
    return variations      
