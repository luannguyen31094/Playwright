import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
from pyngrok import ngrok
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
# Cho phép tất cả các nguồn gọi API (Bao gồm cả Tunnel từ điện thoại vợ Sếp)
CORS(app, resources={r"/*": {"origins": "*"}})

# Mật khẩu gốc bảo vệ API
API_KEY = "TLadmin123!"

# Cấu hình Kết nối Cứng vào DB Postgres
DB_CONFIG = {
    "host": "127.0.0.1",
    "database": "automation",
    "user": "n8nuser",
    "password": "Luannguyen31094",
    "port": "5432"
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

@app.before_request
def check_auth():
    if request.method == "OPTIONS":
        return # Browser preflight check
    req_key = request.headers.get("X-API-KEY")
    if req_key != API_KEY:
        return jsonify({"error": "Sai API KEY!"}), 401

@app.route('/webhook/get-data', methods=['GET'])
def webhook_login():
    req_key = request.headers.get('X-API-KEY')
    if req_key != API_KEY:
        return jsonify({"error": "Sai API KEY!"}), 401
    
    # Kèm thêm Chữ ký Máy chủ (Server Signature) để Frontend tin tưởng đây là Server chính chủ
    return jsonify({
        "success": True, 
        "message": "Login OK",
        "server_signature": "TLAdmin_Automation_V1_Secured"
    })

@app.route('/api/get-data', methods=['GET'])
def get_data():
    req_type = request.args.get('type')
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if req_type == 'scripts':
            cur.execute("SELECT * FROM aff_video_templates ORDER BY id DESC")
            # Map column category_slug to category for frontend
            rows = cur.fetchall()
            for r in rows:
                r['category'] = r.get('category_slug', '')
                r['gender'] = r.get('target_gender', '')
                r['style_slug'] = r.get('visual_style_slug', '')
            return jsonify(rows)
            
        elif req_type == 'scoring':
            cur.execute("SELECT * FROM scoring_criteria ORDER BY id DESC")
            return jsonify(cur.fetchall())
            
        elif req_type == 'history':
            entity_type = request.args.get('entity_type')
            entity_id = request.args.get('entity_id')
            cur.execute("SELECT * FROM record_history WHERE table_name=%s AND record_id=%s ORDER BY saved_at DESC", (entity_type, entity_id))
            return jsonify(cur.fetchall())
            
        elif req_type == 'music':
            cur.execute("SELECT * FROM aff_music_library ORDER BY id DESC LIMIT 500")
            return jsonify(cur.fetchall())
            
        elif req_type == 'products':
            cat = request.args.get('categoryid', '')
            rank = request.args.get('final_rank', '')
            todate = request.args.get('todate', '')
            fromdate = request.args.get('fromdate', '')
            statusvideo = request.args.get('statusvideo', '')
            
            cur.execute("""
                SELECT data FROM public.fnc_get_product_web(%s, %s, %s, %s, %s)
            """, (cat, rank, todate, fromdate, statusvideo))
            
            row = cur.fetchone()
            if row and row['data']:
                return jsonify(row['data'])
            return jsonify([])
            
        elif req_type == 'product_score_details':
            product_id = request.args.get('product_id')
            cur.execute("""
                SELECT 
                    COALESCE(( SELECT scoring_criteria.score
                               FROM scoring_criteria
                              WHERE scoring_criteria.item_key::text = 'commission_amount'::text AND COALESCE(apa.commission_amount, 6000::numeric) >= scoring_criteria.min_val AND COALESCE(apa.commission_amount, 6000::numeric) <= scoring_criteria.max_val
                             LIMIT 1), 0) AS score_amount,
                    COALESCE(( SELECT scoring_criteria.score
                               FROM scoring_criteria
                              WHERE scoring_criteria.item_key::text = 'commission_rate'::text AND COALESCE(apa.commission_rate, 15::numeric) >= scoring_criteria.min_val AND COALESCE(apa.commission_rate, 15::numeric) <= scoring_criteria.max_val
                             LIMIT 1), 0) AS score_rate,
                    COALESCE(( SELECT scoring_criteria.score
                               FROM scoring_criteria
                              WHERE scoring_criteria.item_key::text = 'total_sold'::text AND COALESCE(apa.total_sold, 600)::numeric >= scoring_criteria.min_val AND COALESCE(apa.total_sold, 600)::numeric <= scoring_criteria.max_val
                             LIMIT 1), 0) AS score_sold,
                    COALESCE(( SELECT scoring_criteria.score
                               FROM scoring_criteria
                              WHERE scoring_criteria.item_key::text = 'product_rating'::text AND COALESCE(apa.product_rating, 4.3) >= scoring_criteria.min_val AND COALESCE(apa.product_rating, 4.3) <= scoring_criteria.max_val
                             LIMIT 1), 0) AS score_prating,
                    COALESCE(( SELECT scoring_criteria.score
                               FROM scoring_criteria
                              WHERE scoring_criteria.item_key::text = 'shop_rating'::text AND COALESCE(apa.shop_rating, 0::numeric) >= scoring_criteria.min_val AND COALESCE(apa.shop_rating, 0::numeric) <= scoring_criteria.max_val
                             LIMIT 1), 15) AS score_srating,
                    COALESCE(( SELECT scoring_criteria.score
                               FROM scoring_criteria
                              WHERE scoring_criteria.item_key::text = 'stock_level'::text AND COALESCE(apa.stock_level, 1000)::numeric >= scoring_criteria.min_val AND COALESCE(apa.stock_level, 1000)::numeric <= scoring_criteria.max_val
                             LIMIT 1), 0) AS score_stock
                FROM aff_product_analysis apa
                WHERE apa.id = %s
            """, (product_id,))
            row = cur.fetchone()
            return jsonify(row if row else {})
            
        elif req_type == 'models':
            cur.execute("SELECT * FROM aff_models ORDER BY id DESC")
            return jsonify(cur.fetchall())
            
        elif req_type == 'config':
            cur.execute("SELECT * FROM system_config ORDER BY id ASC")
            return jsonify(cur.fetchall())
            
        else:
            return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/save-data', methods=['POST'])
def save_data():
    payload = request.json
    req_type = payload.get('type')
    data = payload.get('data', {})
    
    conn = get_db()
    cur = conn.cursor()
    try:
        if req_type == 'scripts':
            t_id = data.get('id')
            t_name = data.get('template_name', '')
            c_slug = data.get('category', '')
            gender = data.get('gender', 'Nam')
            p_type = data.get('product_type_id')
            if p_type == '': p_type = None
            s_slug = data.get('style_slug', '')
            is_act = data.get('is_active', True)
            is_def = data.get('is_default', False)
            shots = json.dumps(data.get('shots_json', []))
            
            if t_id: # UPDATE
                cur.execute("""
                    UPDATE aff_video_templates 
                    SET template_name=%s, category_slug=%s, target_gender=%s, product_type_id=%s, 
                        visual_style_slug=%s, is_active=%s, is_default=%s, shots_json=%s, updated_at=NOW()
                    WHERE id=%s
                """, (t_name, c_slug, gender, p_type, s_slug, is_act, is_def, shots, t_id))
                
                # Lưu vào Lịch sử (Dành cho chức năng Undo trên giao diện)
                cur.execute("""
                    INSERT INTO record_history (table_name, record_id, snapshot_json, saved_by)
                    VALUES (%s, %s, %s, %s)
                """, ('scripts', t_id, json.dumps(data), 'Admin'))
            else: # CREATE POST
                cur.execute("""
                    INSERT INTO aff_video_templates 
                    (template_name, category_slug, target_gender, product_type_id, visual_style_slug, is_active, is_default, shots_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (t_name, c_slug, gender, p_type, s_slug, is_act, is_def, shots))
            
            conn.commit()
            return jsonify({"success": True})
            
        elif req_type == 'scoring':
            s_id = data.get('id')
            g_name = data.get('group_name', 'FINANCE')
            i_key = data.get('item_key', '')
            min_v = data.get('min_val', 0)
            max_v = data.get('max_val', 0)
            score = data.get('score', 0)
            note = data.get('rank_bonus_note', '')
            is_act = data.get('is_active', True)
            
            if s_id: # UPDATE
                cur.execute("""
                    UPDATE scoring_criteria
                    SET group_name=%s, item_key=%s, min_val=%s, max_val=%s, score=%s, rank_bonus_note=%s, is_active=%s
                    WHERE id=%s
                """, (g_name, i_key, min_v, max_v, score, note, is_act, s_id))
            else: # CREATE POST
                cur.execute("""
                    INSERT INTO scoring_criteria
                    (group_name, item_key, min_val, max_val, score, rank_bonus_note, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (g_name, i_key, min_v, max_v, score, note, is_act))
            
            conn.commit()
            return jsonify({"success": True})
            
        elif req_type == 'music_toggle':
            s_id = data.get('id')
            is_act = data.get('is_active')
            cur.execute("UPDATE aff_music_library SET is_active=%s WHERE id=%s", (is_act, s_id))
            conn.commit()
            return jsonify({"success": True})
            
        elif req_type == 'models':
            s_id = data.get('id')
            name = data.get('name', '')
            gender = data.get('gender', '')
            age = data.get('age_range', '')
            style = data.get('style_tag', '')
            is_act = data.get('is_active', True)
            if s_id:
                cur.execute("UPDATE aff_models SET name=%s, gender=%s, age_range=%s, style_tag=%s, is_active=%s WHERE id=%s",
                            (name, gender, age, style, is_act, s_id))
            else:
                cur.execute("INSERT INTO aff_models (name, gender, age_range, style_tag, is_active) VALUES (%s, %s, %s, %s, %s)",
                            (name, gender, age, style, is_act))
            conn.commit()
            return jsonify({"success": True})
            
        elif req_type == 'config':
            s_id = data.get('id')
            v_name = data.get('variable_name', '')
            v_val = data.get('variable_value', '')
            desc = data.get('description', '')
            if s_id:
                cur.execute("UPDATE system_config SET variable_name=%s, variable_value=%s, description=%s WHERE id=%s",
                            (v_name, v_val, desc, s_id))
            else:
                cur.execute("INSERT INTO system_config (variable_name, variable_value, description) VALUES (%s, %s, %s)",
                            (v_name, v_val, desc))
            conn.commit()
            return jsonify({"success": True})
            
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    # Start Ngrok Tunnel Automatically
    try:
        ngrok.set_auth_token("2wGl6l5yPeFeLF5DMHY2qXFBv2Y_A6Nxgv5upTZSaQjnzYfp")
        public_url = ngrok.connect(5000).public_url
        print(f"\n=======================================================")
        print(f"🚀 LINK API DÀNH RIÊNG CHO SẾP COPY VÀO ĐĂNG NHẬP:")
        print(f"{public_url}")
        print(f"=======================================================\n")
        
        # Bắn Link sang list N8N Webhooks
        try:
            import requests
            n8n_domains = [
                "openly-joint-dane.ngrok-free.app",
                "thorough-macaw-thankfully.ngrok-free.app",
                "bunny-funky-correctly.ngrok-free.app",
                "lasting-raptor-accurately.ngrok-free.app",
                "evidently-charmed-pegasus.ngrok-free.app"
            ]
            
            print(f"📡 Đang bắn tín hiệu API sang {len(n8n_domains)} trạm N8N (bằng phương thức GET)...")
            msg_content = "🚀 LINK API DÀNH RIÊNG CHO SẾP COPY VÀO ĐĂNG NHẬP:\n👉 " + public_url + " 👈"
            
            for domain in n8n_domains:
                try:
                    # Thay đổi đuôi webhook nếu sếp dùng tên khác (ví dụ: /webhook/something)
                    webhook_url = f"https://{domain}/webhook/something"
                    
                    # Gửi GET request với query parameter ?api_url=... và ?text=...
                    res = requests.get(webhook_url, params={"api_url": public_url, "text": msg_content}, timeout=2)
                    if res.status_code == 200:
                        print(f"  [+] Trúng đích: {domain}")
                except Exception:
                    pass # Ignore errors, cứ bắn đại qua hết
                    
            print("🏁 Đã rải tham số xong!")
                
        except Exception as err_w:
            print(f"⚠️ Lỗi module rải Webhook: {str(err_w)}")
            
    except Exception as e:
        print(f"⚠️ Không thể khởi tạo Ngrok: {str(e)}")
        
    app.run(host='0.0.0.0', port=5000, debug=False)
