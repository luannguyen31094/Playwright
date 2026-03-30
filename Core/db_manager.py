import json,time
from datetime import datetime
from Core.database_info import get_db_connection # Dùng lại file sếp đã có

def now(): return time.strftime('%H:%M:%S')

# --- 1. QUẢN LÝ NHẬT KÝ (execution_logs) ---

def init_execution_log(exec_id, worker_id, task_type, payload):
    """Khởi tạo dòng log khi nhận được yêu cầu từ n8n"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO public.execution_logs (execution_id, worker_id, task_type, payload, status)
                VALUES (%s, %s, %s, %s, 'waiting')
                RETURNING id
            """
            cur.execute(sql, (exec_id, worker_id, task_type, json.dumps(payload)))
            new_id = cur.fetchone()[0]
            conn.commit()
            return new_id
    except Exception as e:
        print(f"❌ [DB_LOG] Lỗi tạo log: {e}")
        return None
    finally:
        if conn: conn.close()

def update_execution_result(log_id, status, result=None, error=None):
    """Cập nhật kết quả cuối cùng của tác vụ"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = """
                UPDATE public.execution_logs 
                SET status = %s, result = %s, error_detail = %s, end_time = NOW()
                WHERE id = %s
            """
            cur.execute(sql, (status, json.dumps(result) if result else None, error, log_id))
            conn.commit()
    except Exception as e:
        print(f"❌ [DB_LOG] Lỗi cập nhật log {log_id}: {e}")
    finally:
        if conn: conn.close()

def get_api_payload_template(endpoint_name):
    """Retrieve dynamic JSON payload template from DB"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT payload_schema FROM public.api_payload_templates WHERE endpoint_name = %s", (endpoint_name,))
            res = cur.fetchone()
            if res:
                return res[0]
            return None
    except Exception as e:
        print(f"❌ [DB] Lỗi lấy template API: {e}")
        return None
    finally:
        if conn: conn.close()

# ---- 2. bactch check
def get_tasks_to_check(batch_id):
    """Lấy danh sách shot đang chờ render"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, worker_id, ticket_id, shot_index FROM veo3_tasks WHERE batch_id = %s AND status_id = 3", (batch_id,))
            return cur.fetchall()
    finally:
        if conn: conn.close()

def get_stranded_tasks_by_project(project_id):
    """Lấy danh sách shot bị kẹt ở status 1, 2, 3, 4 dựa trên project_id để final check"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, worker_id, ticket_id, shot_index FROM veo3_tasks WHERE project_id = %s AND status_id IN (1, 2, 3, 4)", (project_id,))
            return cur.fetchall()
    finally:
        if conn: conn.close()

def force_kill_stranded_tasks(task_ids):
    """Trảm quyết: Tất cả những task_id chốt sổ xong mà vẫn nằm lỳ ở Status 4 (Do không tìm thấy ticket/lỗi) thì ÉP VỀ 6"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            task_ids_int = [int(i) for i in task_ids if str(i).isdigit()]
            if task_ids_int:
                cur.execute("UPDATE veo3_tasks SET status_id = 6, comment = 'Bị Hủy (Ticket hết hạn hoặc Worker lỗi rỗng)' WHERE status_id = 4 AND id = ANY(%s)", (task_ids_int,))
                conn.commit()
    finally:
        if conn: conn.close()

def set_tasks_checking(task_ids):
    """Đánh dấu các shot đang được quét"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE veo3_tasks SET status_id = 4, comment = 'Đang quét...' WHERE id = ANY(%s)", (task_ids,))
            conn.commit()
    finally:
        if conn: conn.close()
        
def set_tasks_status(task_ids, status_id, comment):
    """Cập nhật trạng thái và comment cho một mảng các task"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            task_ids_int = [int(i) for i in task_ids if str(i).isdigit()]
            if task_ids_int:
                cur.execute("UPDATE veo3_tasks SET status_id = %s, comment = %s WHERE id = ANY(%s)", (status_id, comment, task_ids_int))
                conn.commit()
    finally:
        if conn: conn.close()

def update_task_by_ticket(ticket_id, status_id, comment, veo_id=None, url=None):
    """Cập nhật kết quả cuối cùng từ Ticket"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = "UPDATE veo3_tasks SET status_id = %s, comment = %s, veo_video_id = COALESCE(%s, veo_video_id), video_url = COALESCE(%s, video_url), updated_at = now() WHERE ticket_id = %s"
            cur.execute(sql, (status_id, comment, veo_id, url, ticket_id))
            conn.commit()
    finally:
        if conn: conn.close()

# ---- 3. BACTCH VIDEO
def insert_initial_task(batch_id, project_id, shot):
    """Khởi tạo hoặc cập nhật shot video (UPSERT)"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sql = """
            INSERT INTO veo3_tasks (batch_id, project_id, shot_index, worker_id, prompt, status_id)
            VALUES (%s, %s, %s, %s, %s, 1) 
            ON CONFLICT (project_id, shot_index) 
            DO UPDATE SET batch_id = EXCLUDED.batch_id, worker_id = EXCLUDED.worker_id, 
                          prompt = EXCLUDED.prompt, status_id = 1, updated_at = now()
            RETURNING id
        """
        params = (batch_id, project_id, shot['shot_index'], shot['worker_id'], shot['prompt'])
        cur.execute(sql, params)
        db_id = cur.fetchone()[0]
        conn.commit()
        return db_id
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Lỗi UPSERT: {e}")
        raise e
    finally:
        if cur: cur.close()
        if conn: conn.close()

def update_db_status(db_id, status_id, comment, ticket=None, veo_id=None, url=None):
    """Cập nhật trạng thái vạn năng cho task"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = """
            UPDATE veo3_tasks 
            SET status_id = %s, comment = %s, updated_at = now(),
                ticket_id = COALESCE(%s, ticket_id),
                veo_video_id = COALESCE(%s, veo_video_id),
                video_url = COALESCE(%s, video_url)
            WHERE id = %s
        """
        cur.execute(query, (status_id, comment, ticket, veo_id, url, db_id))
        conn.commit()
        print(f"[{now()}] ✅ DB Updated Task {db_id} -> Status ID: {status_id}")
    except Exception as e:
        if conn: conn.rollback()
        print(f"[{now()}] ❌ Lỗi DB Update: {str(e)}")
    finally:
        if conn: conn.close()     

# ---- SELENIUM
def get_worker_info(key_id):
    """Lấy cấu hình Port và IP của Worker từ DB"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            query = "SELECT port, allowed_ips, status FROM client_registry WHERE LOWER(worker_id) = LOWER(%s)"
            cur.execute(query, (key_id,))
            return cur.fetchone()
    finally:
        if conn: conn.close()

def get_active_selenium_workers():
    """Lấy danh sách các worker đang bật (status = 'On') và bỏ qua admin"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            query = "SELECT worker_id, port FROM client_registry WHERE status = 'On' AND worker_id != 'adminLuan031094' ORDER BY port ASC"
            cur.execute(query)
            return cur.fetchall()
    finally:
        if conn: conn.close()

def update_worker_ips(key_id, allowed_ips):
    """Cập nhật danh sách IP mới cho Worker"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE client_registry SET allowed_ips = %s, updated_at = NOW() WHERE LOWER(worker_id) = LOWER(%s)", (allowed_ips, key_id))
            conn.commit()
    finally:
        if conn: conn.close()

# --- DOWNLOAD
def get_worker_download_info(key_id):
    """Lấy Port và danh sách IP để xác thực tải file"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT port, allowed_ips FROM client_registry WHERE LOWER(worker_id) = LOWER(%s)", (key_id,))
            return cur.fetchone()
    finally:
        if conn: conn.close()


# WORKER
def handle_recaptcha_reborn_db(worker_id, new_profile_name):
    """Xử lý toàn bộ phần SQL để chuẩn bị cho việc tái sinh profile"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Kiểm tra giới hạn retry
            cur.execute("SELECT variable_value FROM system_config WHERE variable_name = 'max_recaptcha_retry'")
            row = cur.fetchone()
            max_retries = int(row[0]) if row else 3 

            cur.execute("SELECT retry_count FROM client_registry WHERE worker_id = %s", (worker_id,))
            current_retry = cur.fetchone()[0] or 0

            if current_retry < max_retries:
                new_retry_count = current_retry + 1
                
                # 2. Cập nhật DB cho bản thể mới
                cur.execute("""
                    UPDATE client_registry SET folder_name = %s, retry_count = %s WHERE worker_id = %s
                """, (new_profile_name, new_retry_count, worker_id))
                
                # 3. Ghi Log cleanup
                cur.execute("""
                    INSERT INTO cleanup_logs (log_date, deleted_count, updated_at) 
                    VALUES (CURRENT_DATE, 1, CURRENT_TIMESTAMP) 
                    ON CONFLICT (log_date) 
                    DO UPDATE SET 
                        deleted_count = cleanup_logs.deleted_count + 1,
                        updated_at = CURRENT_TIMESTAMP;
                """)
                conn.commit()
                return {"status": "success", "new_retry": new_retry_count}
            else:
                return {"status": "error", "error_type": "RECAPTCHA_MAX_REACHED"}
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ [DB_MANAGER] Lỗi Tái sinh: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if conn: conn.close()

def get_worker_full_config(worker_id):
    """Lấy 6 cột: Folder, Project, Status(W), Email, Pass, Status(A)"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            query = """
                SELECT c.folder_name, c.project_id, c.status, 
                       a.email, a.password, a.status as acc_status
                FROM client_registry c
                LEFT JOIN google_accounts a ON c.account_id = a.id
                WHERE c.worker_id = %s
            """
            cur.execute(query, (worker_id,))
            res = cur.fetchone()
            # Đảm bảo luôn trả về tuple 6 phần tử dù có dữ liệu hay không
            return res if res else (None, None, None, None, None, None)
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ [DB_LOG] Lỗi config: {e}")
        return (None, None, None, None, None, None)
    finally:
        if conn: conn.close()

def reset_worker_retry(worker_id):
    """Reset bộ đếm về 0 khi tác vụ hoàn thành rực rỡ"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE client_registry SET retry_count = 0 WHERE worker_id = %s", (worker_id,))
            conn.commit()
    except Exception as e:
        if conn: conn.rollback()
        print(f"[{time.strftime('%H:%M:%S')}] ❌ [DB_MANAGER] Lỗi reset retry: {e}")
    finally:
        if conn: conn.close()        