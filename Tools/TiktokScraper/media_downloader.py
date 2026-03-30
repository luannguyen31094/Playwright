import os
import sys
import json
import subprocess
import requests
import time
import psycopg2
from psycopg2.extras import RealDictCursor

# Thêm đường dẫn Core vào sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Tools.TiktokScraper.tiktok_db import get_affiliate_connection, now

def get_pending_media_campaigns(tiktok_product_id=None):
    """Lấy danh sách các campaign đang pending cần tải hình ảnh và crop."""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT 
                    v.id as campaign_id,
                    a.tiktok_product_id,
                    v.local_dir,
                    p.image_urls,
                    a.crop_coords,
                    a.music_vibe
                FROM public.aff_vid_campaigns v
                JOIN public.aff_products p ON v.product_id = p.id
                JOIN public.aff_product_analysis a ON p.tiktok_product_id = a.tiktok_product_id
                WHERE v.video_status = 'pending' AND v.local_dir IS NOT NULL
            """
            params = []
            if tiktok_product_id:
                sql += " AND a.tiktok_product_id = %s"
                params.append(tiktok_product_id)
                
            cur.execute(sql, tuple(params))
            return cur.fetchall()
    except Exception as e:
        print(f"[{now()}] ❌ [DB_AFFILIATE] Lỗi lấy danh sách campaign: {e}")
        return []
    finally:
        if conn: conn.close()

def update_campaign_status(campaign_id, status):
    """Cập nhật trạng thái chiến dịch."""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.aff_vid_campaigns SET video_status = %s WHERE id = %s",
                (status, campaign_id)
            )
            conn.commit()
    except Exception as e:
        print(f"[{now()}] ❌ [DB_AFFILIATE] Lỗi cập nhật trạng thái campaign {campaign_id}: {e}")
    finally:
        if conn: conn.close()

def download_image(url, save_path):
    """Tải hình ảnh từ URL về máy."""
    try:
        resp = requests.get(url, stream=True, timeout=10)
        if resp.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return True
        else:
            print(f"[{now()}] ❌ Lỗi HTTP {resp.status_code} khi tải ảnh: {url}")
            return False
    except Exception as e:
        print(f"[{now()}] ❌ Lỗi Exception tải ảnh {url}: {e}")
        return False

def process_single_campaign(camp):
    campaign_id = camp['campaign_id']
    local_dir = camp['local_dir']
    image_urls_raw = camp['image_urls']
    crop_coords_raw = camp['crop_coords']
    music_vibe = camp['music_vibe']
    
    print(f"[{now()}] 🎬 Bắt đầu xử lý Campaign ID {campaign_id} (Thư mục: {local_dir})")
    
    os.makedirs(local_dir, exist_ok=True)
    
    # 1. Tải ảnh đầu tiên
    first_image_url = None
    if isinstance(image_urls_raw, list) and len(image_urls_raw) > 0:
        first_image_url = image_urls_raw[0]
    elif isinstance(image_urls_raw, str):
        try:
            urls = json.loads(image_urls_raw)
            if urls and isinstance(urls, list):
                first_image_url = urls[0]
        except:
            pass
            
    if not first_image_url:
        print(f"[{now()}] ⚠️ Không tìm thấy URL ảnh hợp lệ cho. Đánh dấu lỗi.")
        update_campaign_status(campaign_id, 'media_error')
        return

    original_img_path = os.path.join(local_dir, "original_image.jpg")
    print(f"[{now()}] 📥 Đang tải ảnh gốc: {first_image_url} -> {original_img_path}")
    if not download_image(first_image_url, original_img_path):
        update_campaign_status(campaign_id, 'media_error')
        return

    # 2. Xử lý FFMPEG Crop
    cropped_img_path = os.path.join(local_dir, "cropped_image.jpg")
    try:
        # crop_coords format depends on how db stored it. Usually {"x":0,"y":0,"w":100,"h":100} or [x,y,w,h]
        coords = crop_coords_raw
        if isinstance(coords, str):
            coords = json.loads(coords)
            
        if coords:
            w, h, x, y = None, None, None, None
            if isinstance(coords, list) and len(coords) >= 4:
                x, y, w, h = coords[0], coords[1], coords[2], coords[3]
            elif isinstance(coords, dict):
                x = coords.get('x', 0)
                y = coords.get('y', 0)
                w = coords.get('w', 0)
                h = coords.get('h', 0)
                if w == 0 and h == 0 and 'width' in coords:
                    w = coords.get('width', 0)
                    h = coords.get('height', 0)
                    
            if w and h:
                # Dùng subprocess gọi FFMPEG cắt ảnh (lưu đè hoặc hình mới)
                command = [
                    "ffmpeg", "-y", "-i", original_img_path,
                    "-vf", f"crop={w}:{h}:{x}:{y}",
                    cropped_img_path
                ]
                print(f"[{now()}] ✂️  Đang cắt ảnh: {' '.join(command)}")
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                print(f"[{now()}] ✅  Đã cắt xong ảnh: {cropped_img_path}")
            else:
                print(f"[{now()}] ⚠️  crop_coords không chứa w/h hợp lệ, bỏ qua crop.")
        else:
            print(f"[{now()}] ⚠️  Không có dữ liệu crop_coords, bỏ qua thao tác cắt.")
    except Exception as e:
        print(f"[{now()}] ❌ Lỗi trong quá trình cắt FFMPEG: {e}. Thử giữ lại ảnh gốc.")
        
    # 3. Ghi thông tin music_vibe
    if music_vibe:
        music_path = os.path.join(local_dir, "music_vibe.txt")
        try:
            with open(music_path, "w", encoding="utf-8") as f:
                f.write(str(music_vibe))
            print(f"[{now()}] 🎵 Đã lưu music_vibe.txt")
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi lưu music_vibe: {e}")
            
    # Cập nhật thành công
    update_campaign_status(campaign_id, 'media_ready')
    print(f"[{now()}] 🎉 Hoàn thành tải & cắt Media cho Campaign {campaign_id}")
    return True

def notify_webhook(total, success, error, comp_list):
    """Gửi Webhook tổng kết cho N8N"""
    webhook_url = os.getenv("WEBHOOK_URL", "https://thorough-macaw-thankfully.ngrok-free.app/webhook/n8n-callback")
    
    msg = f"Đã xử lý xong {total} chiến dịch Media." if total > 0 else "Không có chiến dịch nào chờ tải mồi."
    
    payload = {
        "task_code": "STEP_6_MEDIA_DOWNLOAD",
        "status": "success",
        "message": msg,
        "data": {
            "total_processed": total,
            "success_count": success,
            "error_count": error,
            "campaigns": comp_list
        }
    }
    
    try:
        print(f"[{now()}] 🚀 Đang gửi Webhook báo cáo về N8N...")
        r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
        if r.status_code == 200:
            print(f"[{now()}] 📲 Đã gửi Webhook N8N (Bước 6)! (HTTP {r.status_code})")
        else:
            print(f"[{now()}] ⚠️ Gửi Webhook thất bại: HTTP {r.status_code}")
    except Exception as e:
         print(f"[{now()}] ❌ Lỗi Timeout/Connection khi gửi Webhook N8N: {e}")

def main():
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        
    print(f"======================================================")
    print(f"   TIKTOK MEDIA DOWNLOADER & CROPPER (FFMPEG)")
    print(f"======================================================")
    
    target_id = None
    if len(sys.argv) > 1:
        target_id = sys.argv[1]
        print(f"[{now()}] 🎯 Chế độ Manual: Chỉ quét Product ID: {target_id}")

    campaigns = get_pending_media_campaigns(tiktok_product_id=target_id)
    if not campaigns:
        print(f"[{now()}] 🟢 Không có chiến dịch Video nào đang chờ tải mồi ảnh.")
        notify_webhook(0, 0, 0, [])
        return
        
    print(f"[{now()}] 📥 Đã tìm thấy {len(campaigns)} chiến dịch đang pending.")
    
    success_count = 0
    error_count = 0
    comp_list = []
    
    for camp in campaigns:
        is_success = process_single_campaign(camp)
        
        comp_list.append({
            "campaign_id": camp['campaign_id'],
            "tiktok_product_id": camp.get('tiktok_product_id', ''),
            "local_dir": camp['local_dir'],
            "status": "media_ready" if is_success else "media_error"
        })
        
        if is_success:
            success_count += 1
        else:
            error_count += 1
            
        time.sleep(2) # Tránh Rate Limit khi tải nhiều

    # Gửi báo cáo tổng kết qua Webhook
    notify_webhook(len(campaigns), success_count, error_count, comp_list)

if __name__ == "__main__":
    main()
