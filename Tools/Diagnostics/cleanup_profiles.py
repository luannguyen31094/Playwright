import os
import shutil
import psycopg2
import time
import sys

# Ép stdout ra UTF-8 để không bị lỗi Emoji khi print trên CMD
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Điều hướng để gọi được Config từ thư mục Tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from Core.database_info import DB_CONFIG, get_sys_var 
    print("✅ [CLEANUP] Đã nạp cấu hình DB từ Core/database_info")
except ImportError:
    print("❌ Lỗi: Không tìm thấy DB_CONFIG trong Core/database_info.py")
    sys.exit(1)

PROFILE_PATH = get_sys_var('ROOT_PATH')
# Đã thêm MediaOutput vào danh sách an toàn theo ý sếp
SAFE_PROFILES = ["Profile_Template","Profile_Template1", "Profile_Admin", "MediaOutput"] 

def permanent_cleanup():
    print("🧹 [HỆ THỐNG] Đang quét và XÓA VĨNH VIỄN Profile rác...")
    
    # 🚀 Bước 0: Bảo vệ các Profile Scraper từ Database Affiliate
    dynamic_safe_profiles = list(SAFE_PROFILES)
    try:
        from Tools.TiktokScraper.tiktok_db import get_affiliate_connection
        conn_aff = get_affiliate_connection()
        cur_aff = conn_aff.cursor()
        cur_aff.execute("SELECT chrome_profile_folder FROM public.tiktok_accounts WHERE chrome_profile_folder IS NOT NULL")
        scraper_folders = [r[0] for r in cur_aff.fetchall()]
        dynamic_safe_profiles.extend(scraper_folders)
        cur_aff.close(); conn_aff.close()
        print(f"🛡️ Đã bật khiên bảo vệ cho {len(scraper_folders)} Profile Scraper từ Database Tiktok Accounts.")
    except Exception as e:
        print(f"⚠️ Không thể nạp danh sách Profile Scraper từ Database, các Folder có chữ 'Scraper' sẽ được bảo vệ mặc định: {e}")

    conn = None
    deleted_count = 0 # 🚀 Bước 1: Khởi tạo bộ đếm
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT folder_name FROM client_registry")
        db_profiles = [row[0] for row in cur.fetchall() if row[0]]
        
        all_folders = [f for f in os.listdir(PROFILE_PATH) if os.path.isdir(os.path.join(PROFILE_PATH, f))]
        
        for folder in all_folders:
            # Bảo vệ Tĩnh + Động + Hardcode tên an toàn
            if folder not in db_profiles and folder not in dynamic_safe_profiles and "Scraper" not in folder:
                target = os.path.join(PROFILE_PATH, folder)
                try:
                    shutil.rmtree(target) 
                    print(f"🔥 Đã hủy diệt vĩnh viễn: {folder}")
                    deleted_count += 1 # 🚀 Bước 2: Tăng bộ đếm khi xóa thành công
                except Exception as e:
                    print(f"⚠️ Kẹt: {folder} (Vẫn đang bị chiếm dụng)")
        
        cur.close(); conn.close()
        
        # 🚀 Bước 3: Triệu hồi hàm ghi log nếu có file bị xóa
        if deleted_count > 0:
            log_deleted_profile(deleted_count)
            print(f"📝 [DATABASE] Đã ghi nhận xóa {deleted_count} Profile.")
        else:
            print("✨ Sạch bong! Không có Profile rác nào để xóa.")

    except Exception as e:
        print(f"❌ Lỗi hệ thống dọn dẹp: {e}")

def log_deleted_profile(count=1):
    """Ghi nhận số lượng profile đã xóa vào DB theo ngày hiện tại"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        query = """
            INSERT INTO cleanup_logs (log_date, deleted_count, updated_at)
            VALUES (CURRENT_DATE, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (log_date) 
            DO UPDATE SET 
                deleted_count = cleanup_logs.deleted_count + EXCLUDED.deleted_count,
                updated_at = CURRENT_TIMESTAMP;
        """
        cur.execute(query, (count,))
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        print(f"❌ Lỗi ghi log dọn dẹp: {e}")        

if __name__ == "__main__":
    permanent_cleanup()