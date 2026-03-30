import os
import sys
import shutil

# Thêm path dự án
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Tools.TiktokScraper.tiktok_db import get_affiliate_connection
# from Tools.VideoChecker.policy_checker import process_campaign_video

from Core.database_info import get_sys_var

ROOT_PATH = get_sys_var('ROOT_PATH') 
SOURCE_DIR = os.path.join(ROOT_PATH, "MediaOutput", "outputs")
DEST_DIR = r"D:\ProductAutomation\ReadyVideos"

def sync_and_organize_videos():
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
        
    print(f"🚀 Bắt đầu quét thư mục Video thành phẩm: {SOURCE_DIR}")
    
    conn = get_affiliate_connection()
    if not conn:
        print("❌ Lỗi kết nối Database")
        return
        
    DEST_DIR_CLEAN = os.path.join(DEST_DIR, "CLEAN")
    DEST_DIR_VIOLATION = os.path.join(DEST_DIR, "VIOLATION")
    for d in [DEST_DIR_CLEAN, DEST_DIR_VIOLATION]:
        if not os.path.exists(d):
            os.makedirs(d)
            
    count = 0
    with conn.cursor() as cur:
        for filename in os.listdir(SOURCE_DIR):
            if filename.endswith(".mp4") and "video_final" in filename:
                import re
                match = re.search(r'^(\d+)', filename)
                if not match:
                    continue
                    
                campaign_id = int(match.group(1))
                cur.execute("SELECT product_id FROM aff_vid_campaigns WHERE id = %s", (campaign_id,))
                row = cur.fetchone()
                
                if row:
                    product_id = row[0]
                    src_path = os.path.join(SOURCE_DIR, filename)
                    new_filename = f"Camp{campaign_id}_{product_id}_final.mp4"
                    
                    try:
                        print(f"🔍 Đang dùng AI gỡ băng kiểm tra Campaign {campaign_id}...")
                        from Tools.VideoChecker.policy_checker import process_campaign_video
                        status = process_campaign_video(campaign_id, src_path)
                        
                        if status == "ready_to_upload":
                            dest_path = os.path.join(DEST_DIR_CLEAN, new_filename)
                            shutil.move(src_path, dest_path)
                            print(f"✅ Đã dọn dẹp VIDEO SẠCH: {new_filename}")
                            count += 1
                        elif status == "policy_violation":
                            dest_path = os.path.join(DEST_DIR_VIOLATION, new_filename)
                            shutil.move(src_path, dest_path)
                            print(f"⚠️ Đã CÁCH LY Video Vi Phạm: {new_filename}")
                        else:
                            print(f"❓ AI Check bị lỗi ({status}), giữ nguyên file để kiểm tra tay.")
                    except Exception as e:
                        print(f"❌ Lỗi khi quét/di chuyển file {filename}: {e}")
                else:
                    print(f"⚠️ Không tìm thấy Campaign ID={campaign_id} trong DB cho file {filename}")
                    
    conn.close()
    print(f"🎉 Hoàn thành! Đã tổ chức và cập nhật trạng thái {count} Video sẵn sàng lên thớt Playwright Upload.")

if __name__ == "__main__":
    sync_and_organize_videos()
