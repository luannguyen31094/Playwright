import os
import psycopg2
from psycopg2.extras import RealDictCursor

# database_info.py – Ưu tiên biến môi trường để tránh lộ secret trong code/Git
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "database": os.environ.get("DB_NAME", "automation"),
    "user": os.environ.get("DB_USER", "n8nuser"),
    "password": os.environ.get("DB_PASSWORD", "Luannguyen31094"),  # Production: đặt DB_PASSWORD trong env
    "port": os.environ.get("DB_PORT", "5432")
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_sys_var(var_name, default=r"D:\ChromeAutomation"):
    """Bốc biến hệ thống từ bảng public.system_config"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur: # Tự động đóng cursor khi xong
            cur.execute("SELECT variable_value FROM public.system_config WHERE variable_name = %s", (var_name,))
            row = cur.fetchone()
            return row[0] if row else default
    except Exception as e:
        print(f"⚠️ [DATABASE_INFO] Lỗi lấy biến {var_name}: {e}")
        return default
    finally:
        if conn:
            conn.close() # Đảm bảo LUÔN LUÔN đóng kết nối, dù lỗi hay không