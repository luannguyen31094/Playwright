import os
import sys

# Define root directory to allow imports
root_dir = r"C:\Users\Admin\DockerFL\n8n-selenium-bridge"
if root_dir not in sys.path:
    sys.path.append(root_dir)

from Tools.TiktokScraper.tiktok_db import get_affiliate_connection

def clear_test_data():
    conn = None
    try:
        print("Đang kết nối vào cơ sở dữ liệu...")
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            tables_to_clear = [
                'aff_product_analysis',
                'aff_products',
                'aff_shops',
                'aff_vid_campaigns',
                'aff_showcases',
                'aff_showcase_items',
                'aff_product_commissions'
            ]
            
            print("Đang xóa dữ liệu các bảng...")
            for table in tables_to_clear:
                try:
                    # TRUNCATE CASCADE to bypass foreign keys automatically
                    cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
                    print(f"✅ Đã xóa sạch dữ liệu bảng: {table}")
                except Exception as table_err:
                    print(f"⚠️ Không thể xóa bảng {table}: {table_err}")
                    conn.rollback() # rollback if one fails, to continue
                    continue
            
            conn.commit()
            print("\n🎉 Hoàn tất việc dọn dẹp Database để test lại!")
    except Exception as e:
         print(f"❌ Lỗi: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        
    # Use ASCII input prompt to prevent charmap errors on Windows CMD
    print("⚠️ CẢNH BÁO: Hành động này sẽ XÓA SẠCH toàn bộ dữ liệu Affiliate.")
    confirm = input("Bạn có chắc chắn muốn dọn dẹp Database để test lại không? (y/n): ")
    if confirm.lower() == 'y':
        clear_test_data()
    else:
        print("Đã hủy quá trình dọn dẹp.")
