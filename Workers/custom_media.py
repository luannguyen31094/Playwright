import os, time, requests, subprocess, sys, re, shutil, json
from flask import Flask, request, jsonify, send_from_directory
from waitress import serve
from concurrent.futures import ThreadPoolExecutor
from Core.database_info import get_sys_var

app = Flask(__name__)

# --- [CẤU HÌNH HỆ THỐNG - QUY HOẠCH VÙNG AN TOÀN] ---
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

# --- HÀM BỔ TRỢ (HELPER) ---
def now(): return time.strftime('%H:%M:%S')

def cleanup_old_jobs():
    """Dọn dẹp các thư mục job cũ (>24h) để tránh đầy ổ cứng"""
    now_ts = time.time()
    protected = ["Assets", "outputs"]
    for folder in os.listdir(BASE_DIR):
        if folder in protected: continue
        f_path = os.path.join(BASE_DIR, folder)
        if os.path.isdir(f_path) and os.stat(f_path).st_mtime < now_ts - 86400:
            shutil.rmtree(f_path, ignore_errors=True)
            print(f"[{now()}] 🧹 Đã dọn dẹp Job cũ: {folder}")

def get_direct_drive_link(url):
    if "drive.google.com" in url:
        file_id_match = re.search(r'd/([^/]+)', url) or re.search(r'id=([^&]+)', url)
        if file_id_match:
            return f"https://drive.google.com/uc?export=download&id={file_id_match.group(1)}"
    return url

def download_one_clip(url, filepath):
    try:
        direct_url = get_direct_drive_link(url)
        headers = {'User-Agent': 'Mozilla/5.0'}
        with requests.get(direct_url, stream=True, timeout=60, headers=headers) as r:
            r.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        return True
    except Exception as e:
        print(f"[{now()}] ❌ Lỗi tải file: {e}")
        return False

def download_bgm(url, job_dir):
    """Ưu tiên tải Cloud từ URL, nếu không có hoặc tải lỗi mới đẩy fallback về nhạc mặc định"""
    bgm_final_path = os.path.join(job_dir, "bgm_downloaded.mp3")
    local_file = os.path.join(ASSETS_DIR, "bgm_chuan.mp3")

    if url and url.strip():
        if download_one_clip(url, bgm_final_path) and os.path.getsize(bgm_final_path) > 1000:
            print(f"[{now()}] ⚡ Tải thành công nhạc từ N8N: {url}")
            return bgm_final_path
            
    if os.path.exists(local_file):
        print(f"[{now()}] ⚡ Dùng nhạc Local Fallback (bgm_chuan.mp3): {local_file}")
        return local_file

    return None

# --- ROUTE CHÍNH: PIPELINE TỔNG HỢP ---
@app.route('/custom_media', methods=['POST'])
def custom_media_pipeline():
    data = request.json
    if data.get('key_id') != SECRET_KEY: return jsonify({"status": "error", "message": "Sai Key!"}), 401

    prefix = data.get('prefix', '1')
    job_id = f"{prefix}_job_{int(time.time() * 1000)}"
    final_filename = data.get('final_filename', f"final_{job_id}.mp4")
    urls = [u for u in data.get('urls', []) if u and u.strip()]
    bgm_url = data.get('bgm_url')
    
    job_dir = os.path.join(BASE_DIR, job_id)
    if not os.path.exists(job_dir): os.makedirs(job_dir)

    try:
        # BƯỚC 1: TẢI VIDEO GỐC
        print(f"[{now()}] 📥 Job {job_id}: Đang tải {len(urls)} clips...")
        raw_paths = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            tasks = [executor.submit(download_one_clip, url, os.path.join(job_dir, f"raw_{i:03d}.mp4")) for i, url in enumerate(urls)]
            raw_paths = [os.path.join(job_dir, f"raw_{i:03d}.mp4") for i in range(len(urls))]
            if not all(t.result() for t in tasks): raise Exception("Tải nguyên liệu thất bại!")
        print(f"   └─ ✅ Đã tải xong {len(raw_paths)} file gốc.")
             
        # BƯỚC 2: CẮT & MUTE (GIÂY 2 ĐẾN 6)
        print(f"[{now()}] ✂️ Bước 2: Đang cắt lấy giây 2-6 và Mute...")
        trimmed_paths = []
        for i, path in enumerate(raw_paths):
            t_path = os.path.join(job_dir, f"trim_{i:03d}.mp4")
            cmd = ['ffmpeg', '-y', '-ss', '2', '-t', '4', '-i', path, '-an', '-c:v', 'libx264', '-preset', 'ultrafast', t_path]
            subprocess.run(cmd, check=True, capture_output=True)
            trimmed_paths.append(t_path)
        print(f"\n   └─ ✅ Đã cắt xong toàn bộ {len(trimmed_paths)} clips.")

        # BƯỚC 3: NỐI CÁC ĐOẠN (CONCAT)
        print(f"[{now()}] 🔗 Bước 3: Đang nối (Concat) các đoạn đã cắt...")
        list_file = os.path.join(job_dir, "concat.txt")
        with open(list_file, "w") as f:
            for p in trimmed_paths: f.write(f"file '{os.path.basename(p)}'\n")
        
        merged_temp = os.path.join(job_dir, "merged_temp.mp4")
        cmd_merge = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', '-y', merged_temp]
        subprocess.run(cmd_merge, check=True, capture_output=True)
        print(f"   └─ ✅ Đã tạo file tạm: merged_temp.mp4")

        # BƯỚC 4: TĂNG TỐC 1.5X & GHÉP NHẠC
        print(f"[{now()}] ⚡ Bước 4: Đang 'vít ga' x1.5 và ghép nhạc...")
        bgm_path = download_bgm(bgm_url, job_dir)
        # 🎯 Thành phẩm cuối cùng đưa vào folder outputs
        final_output_path = os.path.join(OUTPUTS_DIR, final_filename)
        
        if bgm_path:
            print(f"   ├─ 🎵 Phát hiện nhạc nền: {os.path.basename(bgm_path)}")
            cmd_final = [
                'ffmpeg', '-y', '-i', merged_temp, '-i', bgm_path,
                '-vf', "setpts=PTS/1.5,crop=iw:trunc(ih*0.92/2)*2:0:0,pad=iw:trunc(ih/0.92/2)*2:0:(oh-ih)/2:color=black",
                '-map', '0:v:0', '-map', '1:a:0', 
                '-c:v', 'libx264', '-preset', 'ultrafast', '-shortest', final_output_path
            ]
        else:
            print(f"   ├─ ⚠️ Không có nhạc nền, chỉ tăng tốc hình ảnh và cắt đáy 8% + đẩy hình vào giữa...")
            cmd_final = [
                'ffmpeg', '-y', '-i', merged_temp, 
                '-vf', "setpts=PTS/1.5,crop=iw:trunc(ih*0.92/2)*2:0:0,pad=iw:trunc(ih/0.92/2)*2:0:(oh-ih)/2:color=black", 
                '-c:v', 'libx264', '-preset', 'ultrafast', final_output_path
            ]
            
        subprocess.run(cmd_final, check=True, capture_output=True)
        print(f"   └─ ✅ Đã render xong thành phẩm: {final_filename}")

        # 🧹 BƯỚC DỌN DẸP THÔNG MINH: Xóa thư mục tạm sau khi đã chuyển thành phẩm sang outputs
        # Nếu sếp muốn giữ lại để debug thì có thể comment dòng rmtree này
        print(f"[{now()}] 🧹 Bước 5: Đang dọn dẹp thư mục tạm...")
        shutil.rmtree(job_dir, ignore_errors=True)
        print(f"[{now()}] ✅ Job {job_id} Hoàn tất -> {final_filename}")

        return jsonify({"status": "success", "job_id": job_id, "filename": final_filename, "download_url": f"/download_final/{final_filename}"})

    except Exception as e:
        print(f"[{now()}] ❌ Lỗi Pipeline: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def _safe_filename(name):
    """Chặn path traversal: chỉ cho phép tên file an toàn (basename, không có ..)."""
    if not name or ".." in name or os.path.sep in name:
        return None
    return os.path.basename(name)

# --- ROUTE TẢI FILE ---
@app.route('/download_final/<filename>')
def download_final_file(filename):
    safe_name = _safe_filename(filename)
    if not safe_name:
        return jsonify({"error": "Tên file không hợp lệ"}), 400
        
    old_file_path = os.path.join(OUTPUTS_DIR, safe_name)
    if os.path.exists(old_file_path):
        print(f"[{now()}] ✅ Tìm thấy {safe_name} ở bãi gốc (ChromeAutomation)")
        return send_from_directory(OUTPUTS_DIR, safe_name)
        
    # Lớp 2: Rà soát bãi lưu trữ Product VIP
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
                
    print(f"[{now()}] ❌ Video {safe_name} không tìm thấy!")
    return jsonify({"error": "File not found anywhere"}), 404

@app.route('/download/<job_id>/<filename>')
def download_file(job_id, filename):
    safe_job = _safe_filename(job_id)
    safe_name = _safe_filename(filename)
    if not safe_job or not safe_name:
        return jsonify({"error": "Tên file không hợp lệ"}), 400
    return send_from_directory(os.path.join(BASE_DIR, safe_job), safe_name)

if __name__ == '__main__':
    current_port = int(sys.argv[1]) if len(sys.argv) > 1 else 9001
    
    # --- GIAO DIỆN TÓM TẮT CHI TIẾT ---
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*80)
    print(f" 🎬 CUSTOM MEDIA PIPELINE V9.3 - HỆ THỐNG XỬ LÝ VIDEO TỰ ĐỘNG")
    print(f" 👤 Quản trị: LUAN ULTRA | 🟢 Cổng: {current_port} | 🔥 Target: 50 Video/Day")
    print("="*80)
    
    print(f" 📁 QUY HOẠCH ĐƯỜNG DẪN (AN TOÀN):")
    print(f"  ├─ 📦 Thư mục mẹ  : {BASE_DIR}")
    print(f"  ├─ 📥 Kho nguyên liệu: {ASSETS_DIR}")
    print(f"  └─ 📤 Kho thành phẩm: {OUTPUTS_DIR}")
    print("-" * 80)
    
    print(" 🛠️ QUY TRÌNH PIPELINE TỰ ĐỘNG (5 BƯỚC):")
    print("  1. 📥 Tải đa luồng clips từ URL (Drive/Direct)")
    print("  2. ✂️ Cắt lấy giây 2-6 & Mute âm thanh gốc")
    print("  3. 🔗 Nối các đoạn đã cắt thành video dài")
    print("  4. ⏩ Tăng tốc 1.5x (Lách bản quyền hình ảnh)")
    print("  5. 🎵 Chèn nhạc (Ưu tiên Assets/bgm_chuan.mp3)")
    print("-" * 80)
    
    print(" 📋 THAM SỐ JSON CHO n8n (POST /custom_media):")
    print(" {")
    print('   "key_id": "<MEDIA_SECRET_KEY từ env hoặc cấu hình>",')
    print('   "urls": ["url1", "url2", "..."],')
    print('   "bgm_url": "link_nhac_cloud",')
    print('   "final_filename": "video_ngon.mp4"')
    print(" }")
    print("-" * 80)
    
    cleanup_old_jobs()
    print(f" [{now()}] ⚙️  Custom Media đang chờ lệnh tại: http://0.0.0.0:{current_port}")
    print("="*80 + "\n")

    serve(app, host='0.0.0.0', port=current_port, threads=20)