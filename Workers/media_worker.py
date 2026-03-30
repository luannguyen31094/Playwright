import os, time, requests, subprocess, shutil, json
from flask import Flask, request, jsonify, send_from_directory
from waitress import serve
from concurrent.futures import ThreadPoolExecutor
from Core.database_info import get_sys_var

app = Flask(__name__)

# --- [CẤU HÌNH HỆ THỐNG - QUY HOẠCH VỀ MEDIAOUTPUT] ---
# Đặt MEDIA_SECRET_KEY trong env (production) thay vì hardcode
SECRET_KEY = os.environ.get("MEDIA_SECRET_KEY", "adminLuan031094")

# 🎯 Bốc ROOT_PATH từ DB ra
ROOT_PATH = get_sys_var('ROOT_PATH') 

# Mọi thư mục con đều sinh ra từ ROOT_PATH
BASE_DIR = os.path.join(ROOT_PATH, "MediaOutput")
ASSETS_DIR = os.path.join(BASE_DIR, "Assets")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

MAX_WORKERS = 10 

# Tạo cấu trúc thư mục lồng nhau
for folder in [BASE_DIR, ASSETS_DIR, OUTPUTS_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"✅ Đã tạo/Kiểm tra thư mục: {folder}")

def now(): return time.strftime('%H:%M:%S')

# --- HÀM BỔ TRỢ: LẤY THỜI LƯỢNG VIDEO ---
def get_duration(filename):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def download_one_clip(url, filepath):
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"[{now()}] ❌ Lỗi tải file {filepath}: {e}")
        return False

def cleanup_old_jobs():
    """Chỉ dọn dẹp các thư mục job tạm, không xóa Assets và outputs"""
    now_ts = time.time()
    protected_folders = ["Assets", "outputs"]
    
    for folder in os.listdir(BASE_DIR):
        if folder in protected_folders: continue # 🛡️ Bỏ qua thư mục quan trọng
        
        folder_path = os.path.join(BASE_DIR, folder)
        if os.path.isdir(folder_path) and os.stat(folder_path).st_mtime < now_ts - 86400:
            shutil.rmtree(folder_path, ignore_errors=True)
            print(f"[{now()}] 🧹 Đã dọn dẹp job cũ: {folder}")

# --- [PHẦN 2: NẠP FILE VÀO ASSETS] ---
def prepare_assets(urls, job_dir):
    if not os.path.exists(job_dir): os.makedirs(job_dir)
    tasks = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for i, url in enumerate(urls):
            # Tải vào job_dir để xử lý tạm thời
            filepath = os.path.join(job_dir, f"part_{i:03d}.mp4")
            tasks.append(executor.submit(download_one_clip, url, filepath))
    return all(t.result() for t in tasks)

# --- [PHẦN 3: CÁC ENDPOINT] ---

@app.route('/merge', methods=['POST'])
def merge_video():
    data = request.json
    if data.get('key_id') != SECRET_KEY: return jsonify({"status": "error"}), 401
    
    urls, job_id = data.get('urls', []), data.get('job_id', f"j_{int(time.time())}")
    job_dir = os.path.join(BASE_DIR, job_id)

    if not prepare_assets(urls, job_dir): 
        return jsonify({"status": "error", "message": "Tải clip thất bại!"}), 500

    try:
        list_file_path = os.path.join(job_dir, "list.txt")
        files = sorted([f for f in os.listdir(job_dir) if f.startswith("part_")])
        with open(list_file_path, "w") as f_list:
            for f in files: f_list.write(f"file '{f}'\n")
        
        final_name = f"merge_{job_id}.mp4"
        # 🎯 Lưu thành phẩm vào folder outputs
        output_path = os.path.join(OUTPUTS_DIR, final_name)
        
        cmd = f'ffmpeg -f concat -safe 0 -i "{list_file_path}" -c copy -y "{output_path}"'
        subprocess.run(cmd, shell=True, check=True)
        
        return jsonify({"status": "success", "download_url": f"/download_final/{final_name}"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/merge_fade', methods=['POST'])
def merge_fade():
    data = request.json
    if data.get('key_id') != SECRET_KEY: return jsonify({"status": "error", "message": "Sai Key!"}), 401
    urls, job_id = data.get('urls', []), data.get('job_id')
    job_dir = os.path.join(BASE_DIR, job_id)
    if not os.path.exists(job_dir): os.makedirs(job_dir)
    try:
        for i, url in enumerate(urls[:2]):
            download_one_clip(url, os.path.join(job_dir, f"f_{i}.mp4"))
        
        c0, c1 = os.path.join(job_dir, "f_0.mp4"), os.path.join(job_dir, "f_1.mp4")
        offset = get_duration(c0) - 0.3
        final_name = f"fade_{job_id}.mp4"
        output_path = os.path.join(OUTPUTS_DIR, final_name) # 🎯 Chuyển vào outputs

        filter_str = f"[0:v][1:v]xfade=transition=fade:duration=0.3:offset={offset}[v];[0:a][1:a]acrossfade=d=0.3[a]"
        cmd = ['ffmpeg', '-y', '-i', c0, '-i', c1, '-filter_complex', filter_str, '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'ultrafast', output_path]
        
        subprocess.run(cmd, check=True)
        return jsonify({"status": "success", "job_id": job_id, "filename": final_name, "download_url": f"/download_final/{final_name}"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/edit', methods=['POST'])
def edit_video():
    data = request.json
    if data.get('key_id') != SECRET_KEY: return jsonify({"status": "error", "message": "Sai Key!"}), 401
    job_id, input_filename, action = data.get('job_id'), data.get('filename'), data.get('action')
    job_dir = os.path.join(BASE_DIR, job_id)
    
    # Check nếu file nằm trong outputs hoặc job_dir
    input_path = os.path.join(job_dir, input_filename)
    if not os.path.exists(input_path):
        input_path = os.path.join(OUTPUTS_DIR, input_filename)

    output_name = f"{action}_{input_filename}"
    output_path = os.path.join(OUTPUTS_DIR, output_name) # 🎯 Mọi hậu kỳ trả về outputs

    if not os.path.exists(input_path): return jsonify({"status": "error", "message": "File gốc không tồn tại"}), 404

    if action == 'trim':
        start, duration = data.get('start', '00:00:00'), data.get('duration', '5')
        cmd = ['ffmpeg', '-y', '-ss', str(start), '-t', str(duration), '-i', input_path, '-c', 'copy', output_path]
    elif action == 'speed_15':
        cmd = ['ffmpeg', '-y', '-i', input_path, '-vf', "setpts=PTS/1.5", '-af', "atempo=1.5", '-c:v', 'libx264', '-preset', 'ultrafast', output_path]
    elif action == 'zoom_11':
        cmd = ['ffmpeg', '-y', '-i', input_path, '-vf', "scale=1.1*iw:-1,crop=iw/1.1:ih/1.1", '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'copy', output_path]
    elif action == 'mute':
        cmd = ['ffmpeg', '-y', '-i', input_path, '-an', '-c:v', 'copy', output_path]
    elif action == 'add_bgm':
        bgm_url = data.get('bgm_url')
        bgm_path = os.path.join(ASSETS_DIR, "bgm_temp.mp3") # 🎯 Nhạc nằm trong Assets
        if download_one_clip(bgm_url, bgm_path):
            cmd = ['ffmpeg', '-y', '-i', input_path, '-i', bgm_path, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-shortest', output_path]
        else: return jsonify({"status": "error", "message": "Không tải được nhạc nền"}), 500
    else: return jsonify({"status": "error", "message": "Action không hợp lệ"}), 400

    try:
        subprocess.run(cmd, check=True)
        return jsonify({"status": "success", "job_id": job_id, "filename": output_name, "download_url": f"/download_final/{output_name}"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint tải file từ job tạm
def _safe_filename(name):
    """Chặn path traversal: chỉ cho phép tên file an toàn (basename, không có ..)."""
    if not name or ".." in name or os.path.sep in name:
        return None
    return os.path.basename(name)

@app.route('/download/<job_id>/<filename>')
def download(job_id, filename):
    safe_job = _safe_filename(job_id)
    safe_name = _safe_filename(filename)
    if not safe_job or not safe_name:
        return "Tên file không hợp lệ", 400
    return send_from_directory(os.path.join(BASE_DIR, safe_job), safe_name)

# 🎯 Endpoint tải file từ kho thành phẩm outputs
@app.route('/download_final/<filename>')
def download_final(filename):
    safe_name = _safe_filename(filename)
    if not safe_name:
        return "Tên file không hợp lệ", 400
        
    old_file_path = os.path.join(OUTPUTS_DIR, safe_name)
    if os.path.exists(old_file_path):
        print(f"[{now()}] ✅ Tìm thấy {safe_name} ở bãi gốc (ChromeAutomation)")
        return send_from_directory(OUTPUTS_DIR, safe_name)
        
    product_base_dir = r"D:\ProductAutomation\Product"
    print(f"[{now()}] 🔍 Bị dọn nhà rồi! Đang truy vết {safe_name} bên ProductAutomation...")
    if os.path.exists(product_base_dir):
        for root, dirs, files in os.walk(product_base_dir):
            if safe_name in files:
                print(f"[{now()}] ✅ Đã tóm được {safe_name} trong thư mục: {root}")
                return send_from_directory(root, safe_name)
                
    print(f"[{now()}] ❌ Video {safe_name} không tìm thấy!")
    return "File not found anywhere", 404

@app.route('/download/<path:filename>')
def serve_file_from_disk(filename):
    safe_name = _safe_filename(filename)
    if not safe_name:
        return "Tên file không hợp lệ", 400
    print(f"📦 [SERVICE 9000] Đang bốc file từ ổ D: {safe_name}")
    
    old_file_path = os.path.join(OUTPUTS_DIR, safe_name)
    if os.path.exists(old_file_path):
        return send_from_directory(OUTPUTS_DIR, safe_name)
        
    product_base_dir = r"D:\ProductAutomation\ReadyVideos"
    print(f"[{now()}] 🔍 Bị dọn nhà rồi! Đang truy vết {safe_name} bên ProductAutomation...")
    if os.path.exists(product_base_dir):
        import re
        match = re.search(r'^(\d+)', safe_name)
        search_prefix = f"Camp{match.group(1)}_" if match else None
        
        for root, dirs, files in os.walk(product_base_dir):
            for file in files:
                if file == safe_name or (search_prefix and file.startswith(search_prefix)):
                    print(f"[{now()}] ✅ Đã tóm được {file} trong thư mục: {root}")
                    return send_from_directory(root, file)
                
    print(f"❌ [LỖI] Không thấy file {safe_name} trong {OUTPUTS_DIR} và cũng không thấy ở ReadyVideos")
    return "File không tồn tại trên ổ D sếp ơi!", 404

@app.route('/api/get_image', methods=['GET'])
def serve_image_by_id():
    """Lấy hình ảnh trực tiếp qua DB Affilate (truyền ID)"""
    product_id = request.args.get('id')
    raw = request.args.get('raw', 'false').lower() == 'true'
    
    if not product_id:
        return "Thiếu tham số id", 400
        
    try:
        import sys
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if PROJECT_ROOT not in sys.path:
            sys.path.append(PROJECT_ROOT)
            
        from Tools.TiktokScraper.tiktok_db import get_affiliate_connection
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT v.local_dir 
                FROM aff_vid_campaigns v 
                JOIN aff_products p ON v.product_id = p.id 
                WHERE p.tiktok_product_id = %s
            """, (str(product_id),))
            row = cur.fetchone()
            
        if not row or not row[0]:
            return "Không tìm thấy thư mục local_dir cho ID này", 404
            
        local_dir = row[0]
        if not os.path.exists(local_dir):
            return "Không tìm thấy thư mục trên ổ cứng", 404
            
        import zipfile
        from io import BytesIO
        from flask import send_file
        
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            has_files = False
            for root, _, files in os.walk(local_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        file_path = os.path.join(root, file)
                        # Archive name removes absolute path
                        arcname = os.path.relpath(file_path, local_dir)
                        zf.write(file_path, arcname)
                        has_files = True
                        
        if not has_files:
            return "Thư mục không có hình ảnh nào", 404
            
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"media_{product_id}.zip"
        )
    except Exception as e:
        print(f"❌ Lỗi serve_image_by_id: {e}")
        return str(e), 500

if __name__ == '__main__':
    import sys
    current_port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    
    # --- GIAO DIỆN ĐIỀU KHIỂN CHI TIẾT ---
    os.system('cls' if os.name == 'nt' else 'clear') # Dọn màn hình cho đẹp
    print("="*80)
    print(f" 🚀 MEDIA WORKER V9.3 - CƠ CHẾ ĐIỀU PHỐI CÔNG NGHIỆP (50 VIDEO/NGÀY)")
    print(f" 👤 Quản trị: LUAN ULTRA | 🟢 Trạng thái: ACTIVE | 🛠️ Port: {current_port}")
    print("="*80)
    
    print(f" 📁 QUY HOẠCH ĐƯỜNG DẪN (VÙNG AN TOÀN):")
    print(f"  ├─ 📦 Gốc (BASE)   : {BASE_DIR}")
    print(f"  ├─ 📥 Nguyên liệu  : {ASSETS_DIR} (Chứa BGM, Logo, Ảnh)")
    print(f"  └─ 📤 Thành phẩm  : {OUTPUTS_DIR} (Chứa Video đã ghép)")
    print("-" * 80)
    
    print(" 📍 DANH SÁCH ENDPOINT & THAM SÓ CHI TIẾT:")
    print("  1. [POST] /merge      -> Ghép nối video (Siêu nhanh - Không render lại)")
    print("     └─ Body: { 'urls': [], 'job_id': '...' }")
    
    print("  2. [POST] /merge_fade -> Ghép chuyển cảnh mờ chồng (0.3s)")
    print("     └─ Body: { 'urls': [clip1, clip2], 'job_id': '...' }")
    
    print("  3. [POST] /edit       -> Hậu kỳ chuyên sâu (Dùng để lách bản quyền)")
    print("     ├─ action: 'trim'     (Cần: 'start', 'duration')")
    print("     ├─ action: 'speed_15' (Tăng tốc x1.5 + Chỉnh Pitch âm thanh)")
    print("     ├─ action: 'zoom_11'  (Phóng to 1.1x + Crop tâm)")
    print("     ├─ action: 'mute'     (Xóa toàn bộ âm thanh gốc)")
    print("     └─ action: 'add_bgm'  (Lồng nhạc nền - Cần: 'bgm_url')")
    print("-" * 80)
    
    print(" 📋 MẪU PAYLOAD CHO n8n (COPY & PASTE):")
    print(" {")
    print('   "key_id": "<MEDIA_SECRET_KEY từ env hoặc cấu hình>",')
    print('   "job_id": "Video_01",')
    print('   "action": "zoom_11",')
    print('   "filename": "merge_Video_01.mp4"')
    print(" }")
    print("-" * 80)
    
    print(f" [{now()}] 🧹 Đang tự động quét và dọn dẹp các Job tạm cũ (>24h)...")
    cleanup_old_jobs()
    
    print(f" [{now()}] ⚙️  Hệ thống đang lắng nghe tại: http://0.0.0.0:{current_port}")
    print("="*80 + "\n")

    serve(app, host='0.0.0.0', port=current_port, threads=20)