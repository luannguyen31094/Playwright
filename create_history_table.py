import psycopg2
import sys
sys.path.append('C:\\Users\\Admin\\DockerFL\\n8n-selenium-bridge')
from Tools.TiktokScraper.tiktok_db import get_affiliate_connection

def create_history_table():
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.sys_script_history (
                    id SERIAL PRIMARY KEY,
                    script_id INTEGER NOT NULL,
                    template_name VARCHAR(255),
                    category VARCHAR(100),
                    gender VARCHAR(50),
                    product_type_id INTEGER,
                    style_slug VARCHAR(100),
                    is_active BOOLEAN,
                    is_default BOOLEAN,
                    shots_json JSONB,
                    saved_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    saved_by VARCHAR(50) DEFAULT 'WebUI'
                );

                COMMENT ON TABLE public.sys_script_history IS 'Bảng lưu trữ lịch sử chỉnh sửa kịch bản từ Dashboard Web UI phục vụ tính năng Undo / Phục hồi';
                COMMENT ON COLUMN public.sys_script_history.script_id IS 'ID của kịch bản gốc trong bảng aff_video_templates';
                COMMENT ON COLUMN public.sys_script_history.saved_at IS 'Thời điểm lưu bản nháp này';
            """)
            conn.commit()
            print("Đã tạo bảng sys_script_history thành công!")
    except Exception as e:
        print("Lỗi:", e)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_history_table()
