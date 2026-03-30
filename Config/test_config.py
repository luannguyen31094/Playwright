import psycopg2
from database_info import DB_CONFIG

print("--- Đang kiểm tra thông tin cấu hình ---")
for key, value in DB_CONFIG.items():
    # Không in mật khẩu để bảo mật nếu cần, nhưng ở đây để bạn tự check
    print(f"{key}: {value}")

try:
    print("\n--- Đang thử kết nối... ---")
    conn = psycopg2.connect(**DB_CONFIG)
    print("✅ Kết nối thành công! File cấu hình hoàn toàn chính xác.")
    conn.close()
except Exception as e:
    print(f"❌ Kết nối thất bại.")
    print(f"Lỗi chi tiết: {e}")