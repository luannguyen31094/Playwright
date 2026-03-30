# -*- coding: utf-8 -*-
import sys
sys.path.append('C:\\Users\\Admin\\DockerFL\\n8n-selenium-bridge')
from Tools.TiktokScraper.tiktok_db import get_affiliate_connection

def add_comments():
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            comments_sql = [
                "COMMENT ON TABLE public.aff_video_templates IS 'Bảng lưu trữ đa dạng kịch bản góc quay sinh video tự động (nhiều góc) phục vụ n8n. Phân tầng theo Category, Gender và Style.';",
                "COMMENT ON COLUMN public.aff_video_templates.id IS 'Khóa chính, tự nhảy số';",
                "COMMENT ON COLUMN public.aff_video_templates.template_name IS 'Tên gợi nhớ kịch bản (VD: Kịch bản Áo Nam đi bộ, Review Túi xách, Đồ ăn vặt...)';",
                "COMMENT ON COLUMN public.aff_video_templates.category IS 'Lưu text phân loại gốc gợi nhớ (VD: Thời trang nam, Điện tử, Mỹ phẩm)';",
                "COMMENT ON COLUMN public.aff_video_templates.gender IS 'Lưu giới tính áp dụng (Nam, Nữ, Unisex, All)';",
                "COMMENT ON COLUMN public.aff_video_templates.product_type_id IS 'KHÓA LIÊN KẾT siêu bám vào bảng aff_product_types (ID tương ứng của Loại sản phẩm: Áo, Quần, Giày... Lõi lấy Data của n8n)';",
                "COMMENT ON COLUMN public.aff_video_templates.style_slug IS 'Phân loại Style chuyên sâu trong cùng nhánh SP (lip_sync_nhac, walking_di_bo, detail_macro...)';",
                "COMMENT ON COLUMN public.aff_video_templates.is_active IS 'Trạng thái Bật/Tắt (True=Dùng, False=Ngưng) để ẩn kịch bản cũ mà không cần xóa Data';",
                "COMMENT ON COLUMN public.aff_video_templates.is_default IS 'Đánh dấu đây là Kịch bản gốc vạn năng dùng dự phòng (Fallback) khi 1 sản phẩm chưa có kịch bản chuyên sâu nào khớp lệnh';",
                "COMMENT ON COLUMN public.aff_video_templates.shots_json IS 'ARRAY JSONB CHỨA KỊCH BẢN GỐC - Đóng gói mảng 5/12/N góc quay (VD: [{id: S1, act: Quay ngan...}]). N8N Node móc Data từ đây!';",
            ]
            
            for sql in comments_sql:
                cur.execute(sql)
            conn.commit()
            print("DONE!")
    except Exception as e:
        print("ERR: " + str(e))
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    add_comments()
