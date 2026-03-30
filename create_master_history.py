import psycopg2
import sys
sys.path.append('C:\\Users\\Admin\\DockerFL\\n8n-selenium-bridge')
from Tools.TiktokScraper.tiktok_db import get_affiliate_connection

def create_master_history():
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            # Xóa bảng cũ nếu CÓ
            cur.execute("DROP TABLE IF EXISTS public.sys_script_history;")
            
            # Tạo Siêu Bảng Lịch sử dùng chung
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.sys_dashboard_history (
                    id SERIAL PRIMARY KEY,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id INTEGER NOT NULL,
                    snapshot_json JSONB NOT NULL,
                    saved_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    saved_by VARCHAR(50) DEFAULT 'Admin Web'
                );

                COMMENT ON TABLE public.sys_dashboard_history IS 'Bảng MASTER lưu trữ lịch sử mọi Tab trên Dashboard (Scripts, Scoring, Models...) theo dạng JSON động';
                COMMENT ON COLUMN public.sys_dashboard_history.entity_type IS 'Loại thực thể: scripts, scoring, music, models...';
                COMMENT ON COLUMN public.sys_dashboard_history.entity_id IS 'Khóa chính của thực thể đó';
                COMMENT ON COLUMN public.sys_dashboard_history.snapshot_json IS 'Toàn bộ dữ liệu cột của dòng đó ở thời điểm lưu';
            """)
            conn.commit()
            print("Đã tạo Master Table sys_dashboard_history thành công!")
    except Exception as e:
        print("Lỗi:", e)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_master_history()
