import os
import time
import json
import psycopg2
from psycopg2.extras import RealDictCursor

# --- CẤU HÌNH DB AFFILIATE ---
AFFILIATE_DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "database": os.environ.get("AFFILIATE_DB_NAME", "automation"),
    "user": os.environ.get("DB_USER", "n8nuser"),
    "password": os.environ.get("DB_PASSWORD", "Luannguyen31094"),
    "port": os.environ.get("DB_PORT", "5432")
}

def get_affiliate_connection():
    return psycopg2.connect(**AFFILIATE_DB_CONFIG)

def now(): return time.strftime('%H:%M:%S')

# --- 0. XỬ LÝ CATEGORY ---
def get_or_create_category(slug="unknown", tiktok_category_id="unknown"):
    """Lấy ID danh mục, nếu chưa có thì tạo mới"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO aff_categories (tiktok_category_id, name, slug, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (tiktok_category_id) 
                DO UPDATE SET name = EXCLUDED.name, slug = EXCLUDED.slug, updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """
            cur.execute(sql, (tiktok_category_id, slug, slug))
            conn.commit()
            return cur.fetchone()[0]
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi get_or_create_category: {e}")
        return None
    finally:
        if conn: conn.close()

# --- 1. XỬ LÝ SHOPS ---
def upsert_shop(shop_payload):
    """Thêm mới hoặc cập nhật thông tin Shop (Affiliate DB)"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO aff_shops (id, name, logo_url, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) 
                DO UPDATE SET name = EXCLUDED.name, logo_url = EXCLUDED.logo_url, updated_at = CURRENT_TIMESTAMP
            """
            cur.execute(sql, (
                shop_payload.get("shop_id", ""),
                shop_payload.get("shop_name", ""),
                shop_payload.get("logo_url", "")
            ))
            conn.commit()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi upsert_shop: {e}")
    finally:
        if conn: conn.close()

# --- 2. XỬ LÝ SẢN PHẨM SẢN PHẨM & VIDEO CAMPAIGNS ---
def check_video_campaign_exists(product_id):
    """Kiểm tra xem sản phẩm đã có campaign chưa"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM vid_campaigns WHERE product_id = %s", (product_id,))
            return cur.fetchone() is not None
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi check_video_campaign_exists: {e}")
        return False
    finally:
        if conn: conn.close()

def insert_video_campaign(product_id):
    """Thêm Video Campaign mới vào Affiliate DB"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO vid_campaigns (product_id, video_status)
                VALUES (%s, 'Pending')
                ON CONFLICT DO NOTHING
            """
            cur.execute(sql, (product_id,))
            conn.commit()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi insert_video_campaign: {e}")
    finally:
        if conn: conn.close()

def insert_captcha_log(log_data):
    """Lưu trữ lịch sử giải Captcha vào database"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO aff_captcha_logs (
                    module_name, worker_id, target_type, target_id, 
                    captcha_id, captcha_type, status, recognition_time, 
                    cost, result_raw, page_url, ip_address
                ) VALUES (
                    %(module_name)s, %(worker_id)s, %(target_type)s, %(target_id)s,
                    %(captcha_id)s, %(captcha_type)s, %(status)s, %(recognition_time)s,
                    %(cost)s, %(result_raw)s, %(page_url)s, %(ip_address)s
                )
            """
            cur.execute(sql, log_data)
            conn.commit()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi insert_captcha_log: {e}")
    finally:
        if conn: conn.close()

def get_pending_campaigns(limit=5):
    """Lấy các chiến dịch (sản phẩm) đang chờ tạo video"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT p.id as internal_id, p.tiktok_product_id, p.title, p.image_urls, p.description
                FROM aff_products p
                WHERE p.id IN (
                    SELECT product_id FROM aff_vid_campaigns 
                    WHERE video_status = 'Pending'
                )
                ORDER BY p.id ASC
                LIMIT %s
            """
            cur.execute(sql, (limit,))
            campaigns = cur.fetchall()
            
            if campaigns:
                product_ids = [c['internal_id'] for c in campaigns]
                update_sql = "UPDATE aff_vid_campaigns SET video_status = 'Generating' WHERE product_id = ANY(%s)"
                cur.execute(update_sql, (product_ids,))
                conn.commit()
                
            return campaigns
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi get_pending_campaigns: {e}")
        return []
    finally:
        if conn: conn.close()

def update_campaign_status(product_id, status):
    """Cập nhật trạng thái chiến dịch sau khi cào xong"""
    # Xử lý lowercase status nếu schema sử dụng enum viết thường
    if status.lower() in ['pending', 'processing', 'completed', 'failed']:
        db_status = status.lower()
    else:
        # Nếu gửi trạng thái custom (vd: ReturnToPending), hoặc Error, fallback thành fail
        db_status = 'failed' if 'error' in status.lower() or 'fail' in status.lower() else 'completed'
        
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE aff_vid_campaigns SET video_status = %s WHERE product_id = %s", (db_status, product_id))
            conn.commit()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi update_campaign_status: {e}")
    finally:
        if conn: conn.close()

def upsert_product(product_payload, category_id=None):
    """Thêm mới hoặc cập nhật thông tin Product & Shop (Affiliate DB)"""
    shop_payload = {
        "shop_id": product_payload.get("shop_id", ""),
        "shop_name": product_payload.get("shop_name", ""),
        "logo_url": product_payload.get("shop_logo", "")
    }
    upsert_shop(shop_payload)
    
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            # Upsert into products, returning the internal serial ID
            sql_product = """
                INSERT INTO aff_products (tiktok_product_id, shop_id, category_id, title, image_urls, canonical_url, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (tiktok_product_id) 
                DO UPDATE SET title = EXCLUDED.title, image_urls = EXCLUDED.image_urls, canonical_url = EXCLUDED.canonical_url, category_id = EXCLUDED.category_id
                RETURNING id
            """
            images_json = json.dumps(product_payload.get("image_urls", []))
            
            cur.execute(sql_product, (
                product_payload.get("product_id"), # tiktok_product_id
                product_payload.get("shop_id"),
                category_id,
                product_payload.get("title"),
                images_json,
                product_payload.get("canonical_url", "")
            ))
            
            internal_product_id = cur.fetchone()[0]
            conn.commit()
            return internal_product_id
            
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi upsert_product: {e}")
        return None
    finally:
        if conn: conn.close()

# --- 3. XỬ LÝ METRICS (HISTORY) ---
def upsert_product_analysis(product_payload, metric_payload):
    """Lưu phân tích sản phẩm vào bảng aff_product_analysis mới"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            tiktok_product_id = product_payload.get("product_id")
            title = product_payload.get("title")
            
            sale_price = float(metric_payload.get("sale_price_decimal", 0)) if metric_payload.get("sale_price_decimal") else 0
            origin_price = float(metric_payload.get("origin_price_decimal", 0)) if metric_payload.get("origin_price_decimal") else 0
            discount = float(metric_payload.get("discount_decimal", 0)) if metric_payload.get("discount_decimal") else 0
            total_sold = int(metric_payload.get("sold_count", 0)) if metric_payload.get("sold_count") else 0
            product_rating = float(metric_payload.get("rating_score", 0)) if metric_payload.get("rating_score") else 0
            review_count = int(metric_payload.get("review_count", 0)) if metric_payload.get("review_count") else 0

            upsert_sql = """
                INSERT INTO aff_product_analysis 
                (tiktok_product_id, title, sale_price, origin_price, discount_percent, total_sold, product_rating, review_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tiktok_product_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    sale_price = EXCLUDED.sale_price,
                    origin_price = EXCLUDED.origin_price,
                    discount_percent = EXCLUDED.discount_percent,
                    total_sold = EXCLUDED.total_sold,
                    product_rating = EXCLUDED.product_rating,
                    review_count = EXCLUDED.review_count,
                    updated_at = CURRENT_TIMESTAMP;
            """
            cur.execute(upsert_sql, (tiktok_product_id, title, sale_price, origin_price, discount, total_sold, product_rating, review_count))
            conn.commit()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi upsert_product_analysis: {e}")
    finally:
        if conn: conn.close()

def update_product_description(tiktok_product_id, description):
    """Cập nhật mô tả (description) cho sản phẩm (Task 14)"""
    if not description:
        return
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            sql = """
                UPDATE aff_products 
                SET description = %s
                WHERE tiktok_product_id = %s
            """
            cur.execute(sql, (description, tiktok_product_id))
            conn.commit()
            print(f"[{now()}] 📝 Đã cập nhật Description cho sản phẩm {tiktok_product_id} vào DB.")
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi update_product_description: {e}")
    finally:
        if conn: conn.close()

# --- 4. DATA MAPPING (AFFILIATE VALIDATOR) ---
def add_affiliate_columns_if_missing():
    """Đảm bảo bảng product_metrics có cột is_affiliate và commission_rate"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE aff_product_metrics ADD COLUMN IF NOT EXISTS commission_rate DECIMAL(5, 2)")
            cur.execute("ALTER TABLE aff_product_metrics ADD COLUMN IF NOT EXISTS is_affiliate BOOLEAN DEFAULT TRUE")
            conn.commit()
    except Exception as e:
        pass # Có thể lỗi do thiếu quyền, bỏ qua
    finally:
        if conn: conn.close()
        
def get_high_sales_products_to_check(min_sales=50):
    """Lấy danh sách sản phẩm có lượt bán cao (chưa check hoa hồng) để kiểm tra Affiliate (Task 2)
       Sẽ được skip nếu 'Đây không phải là sản phẩm liên kết'
    """
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT a.tiktok_product_id, a.total_sold, p.description, p.title
                FROM aff_product_analysis a
                LEFT JOIN aff_products p ON p.tiktok_product_id = a.tiktok_product_id
                WHERE a.total_sold >= %s
                AND a.commission_rate IS NULL -- Chỉ lấy những sản phẩm chưa check hoa hồng
                AND a.is_affiliate IS NOT FALSE -- Chưa bị đánh dấu Non-Affiliate
                AND a.is_deleted IS NOT TRUE
                ORDER BY a.captured_at DESC
            """
            cur.execute(sql, (min_sales,))
            return cur.fetchall()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi get_high_sales_products_to_check: {e}")
        return []
    finally:
        if conn: conn.close()
        
def update_product_commission(tiktok_product_id, commission_rate, commission_amount, is_affiliate=True):
    """Cập nhật hoa hồng và lưu vào bảng product_commissions (Dành cho cả LDPlayer & Playwright)"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            # Update metrics in the analysis table
            sql_metrics = """
                UPDATE aff_product_analysis 
                SET commission_rate = %s, commission_amount = %s, is_affiliate = %s, updated_at = CURRENT_TIMESTAMP
                WHERE tiktok_product_id = %s
            """
            cur.execute(sql_metrics, (commission_rate, commission_amount, is_affiliate, tiktok_product_id))
            
            # Record literal commission if found
            if is_affiliate and commission_amount is not None:
                # Tìm ID internal của products (nếu bảng aff_product_commissions vẫn dùng internal ID)
                cur.execute("SELECT id FROM aff_products WHERE tiktok_product_id = %s", (tiktok_product_id,))
                prod = cur.fetchone()
                if prod:
                    internal_id = prod[0]
                    sql_comm = """
                        INSERT INTO aff_product_commissions (product_id, rate_percent, amount, source)
                        VALUES (%s, %s, %s, %s)
                    """
                    cur.execute(sql_comm, (tiktok_product_id, commission_rate, commission_amount, 'Web_Scraper')) # Keep source identifier
                
            conn.commit()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi update_product_commission: {e}")
    finally:
        if conn: conn.close()

# --- 5. SYSTEM LOGS ---
def insert_captcha_log(log_data):
    """Lưu nhật ký giải mã Captcha vào sys_captcha_logs"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO sys_captcha_logs 
                (module_name, worker_id, target_type, target_id, captcha_id, captcha_type, status, recognition_time, cost, result_raw, page_url, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql, (
                log_data.get('module_name'),
                log_data.get('worker_id'),
                log_data.get('target_type'),
                log_data.get('target_id'),
                log_data.get('captcha_id'),
                log_data.get('captcha_type'),
                log_data.get('status'),
                log_data.get('recognition_time'),
                log_data.get('cost'),
                log_data.get('result_raw'),
                log_data.get('page_url'),
                log_data.get('ip_address')
            ))
            conn.commit()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi insert_captcha_log: {e}")
    finally:
        if conn: conn.close()
        
# --- 6. SHOWCASE SYNC ---
def get_or_create_showcase_by_account(tiktok_account_id):
    """Tự động tạo hoặc lấy ID của showcase dựa trên Tiktok Account ID đang chạy"""
    if not tiktok_account_id:
        return 1
    showcase_name = f"Account_{tiktok_account_id}_Showcase"
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM aff_showcases WHERE showcase_name = %s", (showcase_name,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE aff_showcases SET account_id = %s WHERE id = %s AND account_id IS NULL", (tiktok_account_id, row[0]))
                conn.commit()
                return row[0]
            else:
                cur.execute("INSERT INTO aff_showcases (showcase_name, status, account_id) VALUES (%s, 'active', %s) RETURNING id", (showcase_name, tiktok_account_id))
                showcase_id = cur.fetchone()[0]
                conn.commit()
                return showcase_id
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi get_or_create_showcase_by_account: {e}")
        return 1
    finally:
        if conn: conn.close()

def get_all_showcase_product_states(showcase_id=1):
    """Lấy danh sách product_id và trạng thái is_live trong DB cho 1 showcase cụ thể"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT product_id, is_live FROM aff_showcase_items WHERE showcase_id = %s", (showcase_id,))
            rows = cur.fetchall()
            return {str(row[0]): row[1] for row in rows}
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi get_all_showcase_product_states: {e}")
        return {}
    finally:
        if conn: conn.close()

def upsert_showcase_item(showcase_id, product_id, product_name, price, stock, is_live):
    """Cập nhật hoặc Insert thông tin quét được từ Showcase vào CSDL"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            # 1. Kiểm tra xem product_id đã có chưa
            cur.execute("SELECT id FROM aff_showcase_items WHERE showcase_id = %s AND product_id = %s", (showcase_id, product_id))
            row = cur.fetchone()
            
            if row:
                # 2. Đã có -> UPDATE
                update_sql = """
                    UPDATE aff_showcase_items
                    SET product_name = %s, price = %s, stock = %s, is_live = %s, last_synced_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                cur.execute(update_sql, (product_name, price, stock, is_live, row[0]))
                item_id = row[0]
            else:
                # 3. Chưa có -> INSERT
                insert_sql = """
                    INSERT INTO aff_showcase_items 
                    (showcase_id, product_id, product_name, price, stock, is_live, last_synced_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING id
                """
                cur.execute(insert_sql, (showcase_id, product_id, product_name, price, stock, is_live))
                item_id = cur.fetchone()[0]

            conn.commit()
            return item_id
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi upsert_showcase_item: {e}")
        return None
    finally:
        if conn: conn.close()

def sync_showcase_items(showcase_name, products_data, is_pagination_append=False):
    """
    Đồng bộ mảng sản phẩm từ web vào bảng aff_showcase_items,
    Có hỗ trợ phân trang (chưa xóa đồ cũ nếu là trang 2, trang 3).
    """
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            # 1. Lấy hoặc tạo Showcase ID
            cur.execute("SELECT id FROM aff_showcases WHERE showcase_name = %s", (showcase_name,))
            row = cur.fetchone()
            if row:
                showcase_id = row[0]
            else:
                cur.execute("INSERT INTO aff_showcases (showcase_name, status) VALUES (%s, 'active') RETURNING id", (showcase_name,))
                showcase_id = cur.fetchone()[0]
                conn.commit()
                
            # 2. Lấy danh sách ID hiện có thuộc showcase này ĐỂ KIỂM TRA ẨN
            cur.execute("SELECT product_id, is_live FROM aff_showcase_items WHERE showcase_id = %s", (showcase_id,))
            existing_db = {r[0]: r[1] for r in cur.fetchall()} # {tiktok_id: is_live}
            
            incoming_ids = set()
            new_add_count = 0
            update_count = 0
            
            for prod in products_data:
                product_id = str(prod['product_id'])
                incoming_ids.add(product_id)
                rate = prod.get('rate', 0)
                amount = prod.get('amount', 0)
                
                # INSERT hoặc UPDATE vào DB Affiliate Sync
                try:
                    cur.execute("SELECT id FROM aff_showcase_items WHERE showcase_id = %s AND product_id = %s", (showcase_id, product_id))
                    item_id = cur.fetchone()
                    
                    if item_id:
                        # Cập nhật thông tin
                        cur.execute("""
                            UPDATE aff_showcase_items
                            SET confirmed_rate_percent = %s, confirmed_commission_amount = %s,
                                product_name = %s, price = %s, stock = %s, 
                                is_live = true, last_synced_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (rate, amount, prod.get('name'), prod.get('price'), prod.get('stock'), item_id[0]))
                        update_count += 1
                    else:
                        # Thêm mới
                        cur.execute("""
                            INSERT INTO aff_showcase_items 
                            (showcase_id, product_id, product_name, price, stock, confirmed_rate_percent, confirmed_commission_amount, is_live)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, true)
                        """, (showcase_id, product_id, prod.get('name'), prod.get('price'), prod.get('stock'), rate, amount))
                        new_add_count += 1
                        
                except Exception as e_item:
                    print(f"❌ [DB_AFFILIATE] Lỗi lưu item {product_id}: {e_item}")
                    conn.rollback() # Tránh kẹt loop
                    
            if not is_pagination_append:
                # 3. Tính toán các mục cần bị Ẩn (Chỉ chạy khi không phải nối data trang tiếp theo)
                to_hide_ids = []
                for p_id, p_is_live in existing_db.items():
                    if p_id not in incoming_ids and p_is_live:
                         to_hide_ids.append(p_id)
                         
                if to_hide_ids:
                     cur.execute("UPDATE aff_showcase_items SET is_live = false WHERE showcase_id = %s AND product_id = ANY(%s)", (showcase_id, to_hide_ids))
                     
            conn.commit()
            return {"new": new_add_count, "updated": update_count, "to_hide": to_hide_ids if not is_pagination_append else []}
            
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi sync_showcase_items: {e}")
        return {"new": 0, "updated": 0, "to_hide": []}
    finally:
        if conn: conn.close()

# --- 7. VIDEO CAMPAIGN & AI (STEP 5) ---
def get_high_ai_score_products(limit=10):
    """Lấy các sản phẩm có cờ is_video_ready = true chưa nằm trong Showcase"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            # Lấy các sản phẩm tốt, chưa xóa, is_video_ready=true, và lấy ID nội bộ của chúng từ aff_products
            sql = """
                SELECT p.id as internal_id, a.tiktok_product_id, a.title, 
                       a.gender, a.product_type_id, s.id as showcase_item_id, a.pain_point, a.sale_price
                FROM public.aff_product_analysis a
                JOIN public.aff_products p ON a.tiktok_product_id = p.tiktok_product_id
                LEFT JOIN public.aff_showcase_items s ON a.tiktok_product_id = s.product_id
                WHERE a.is_video_ready = true 
                  AND a.is_deleted = false 
                  AND a.is_affiliate = true
                  AND (s.product_id IS NULL OR s.is_live = false)
                ORDER BY a.ai_score DESC NULLS LAST
                LIMIT %s
            """
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            return [{
                "internal_id": r[0], 
                "tiktok_id": r[1], 
                "title": r[2],
                "gender": r[3],
                "product_type_id": r[4],
                "showcase_item_id": str(r[5]) if r[5] else None,
                "ai_prompt": r[6],
                "sale_price": r[7]
            } for r in rows]
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi get_high_ai_score_products: {e}")
        return []
    finally:
        if conn: conn.close()

def create_video_campaign(product_id, gender=None, product_type_id=None, showcase_item_id=None, ai_prompt=None, tiktok_product_id=None, tiktok_id=None):
    """Tạo chiến dịch video mới trên bảng aff_vid_campaigns gốc bằng product_id (Integer) và các metadata khác"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            # Tránh tạo trùng campaign đang xử lý
            cur.execute("SELECT id FROM public.aff_vid_campaigns WHERE product_id = %s", (product_id,))
            if not cur.fetchone():
                
                local_dir = None
                if tiktok_product_id:
                    local_dir = f"D:\\ProductAutomation\\Product\\{tiktok_product_id}"
                    os.makedirs(local_dir, exist_ok=True)
                
                # Biến tiktok_id truyền vào đang là ID integer của bảng tiktok_accounts.
                # Do đó ta cần phải truy vấn lại chuỗi tiktok_id (varchar) thật từ database
                real_tiktok_id = None
                if tiktok_id is not None:
                    cur.execute("SELECT tiktok_id FROM public.tiktok_accounts WHERE id = %s", (tiktok_id,))
                    row = cur.fetchone()
                    if row:
                        real_tiktok_id = row[0]
                    
                sql = """
                    INSERT INTO public.aff_vid_campaigns 
                    (product_id, video_status, gender, product_type_id, showcase_item_id, ai_prompt, local_dir, tiktok_id)
                    VALUES (%s, 'pending', %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                cur.execute(sql, (product_id, gender, product_type_id, showcase_item_id, ai_prompt, local_dir, real_tiktok_id))
                new_id = cur.fetchone()[0]
                conn.commit()
                return new_id
            return None
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi create_video_campaign: {e}")
        return None
    finally:
        if conn: conn.close()

# --- 8. TIKTOK ACCOUNTS (AUTO LOGIN) ---
def get_tiktok_account():
    """Lấy tài khoản TikTok đầu tiên đang active để đăng nhập tự động"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT username, password FROM public.tiktok_accounts WHERE status = 'active' ORDER BY id ASC LIMIT 1")
            return cur.fetchone()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi get_tiktok_account: {e}")
        return None
    finally:
        if conn: conn.close()

def get_tiktok_account_by_id(account_id):
    """Lấy toàn bộ thông tin tài khoản (Folder Profile, Category, Username, ...) từ ID được nhận từ N8N Gateway"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM public.tiktok_accounts WHERE id = %s LIMIT 1", (account_id,))
            return cur.fetchone()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi get_tiktok_account_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def update_tiktok_account_category(account_id, category_id):
    """Cập nhật Category ID hiện tại cho Account đang đi cào"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.tiktok_accounts SET category_id = %s WHERE id = %s",
                (category_id, account_id)
            )
            conn.commit()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi update_tiktok_account_category: {e}")
    finally:
        if conn: conn.close()

def get_tiktok_account_verifier(username):
    """Lấy mã OTP xác minh 2 bước từ cột code_verifier"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT code_verifier FROM public.tiktok_accounts WHERE username = %s LIMIT 1", (username,))
            res = cur.fetchone()
            if res:
                return res[0]
            return None
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi get_tiktok_account_verifier: {e}")
        return None
    finally:
        if conn: conn.close()

def reset_tiktok_account_verifier(username):
    """Reset cột code_verifier về NULL sau khi dùng xong để tránh đụng độ cho lần sau"""
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE public.tiktok_accounts SET code_verifier = NULL WHERE username = %s", (username,))
            conn.commit()
    except Exception as e:
        print(f"❌ [DB_AFFILIATE] Lỗi reset_tiktok_account_verifier: {e}")
    finally:
        if conn: conn.close()
