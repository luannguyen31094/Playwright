# -*- coding: utf-8 -*-
import sys
import json
sys.path.append('C:\\Users\\Admin\\DockerFL\\n8n-selenium-bridge')
from Tools.TiktokScraper.tiktok_db import get_affiliate_connection

def extract_schema():
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            # Lấy tất cả các table và comment
            cur.execute("""
                SELECT 
                    c.relname as table_name,
                    obj_description(c.oid) as table_comment
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                ORDER BY c.relname;
            """)
            tables = cur.fetchall()
            
            schema_data = {}
            for t in tables:
                t_name = t[0]
                t_comment = t[1]
                
                # Lấy tất cả cột và comment
                cur.execute("""
                    SELECT 
                        a.attname as column_name,
                        format_type(a.atttypid, a.atttypmod) as data_type,
                        col_description(a.attrelid, a.attnum) as column_comment
                    FROM pg_attribute a
                    JOIN pg_class c ON c.oid = a.attrelid
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public' AND c.relname = %s AND a.attnum > 0 AND NOT a.attisdropped
                    ORDER BY a.attnum;
                """, (t_name,))
                columns = cur.fetchall()
                
                cols_data = []
                for c in columns:
                    cols_data.append({
                        "name": c[0],
                        "type": c[1],
                        "comment": c[2]
                    })
                    
                schema_data[t_name] = {
                    "comment": t_comment,
                    "columns": cols_data
                }
                
            with open("C:\\Users\\Admin\\DockerFL\\n8n-selenium-bridge\\db_schema_dump.json", "w", encoding="utf-8") as f:
                json.dump(schema_data, f, ensure_ascii=False, indent=2)
            print("Schema dumped successfully to db_schema_dump.json")
            
    except Exception as e:
        print("ERR: " + str(e))
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    extract_schema()
