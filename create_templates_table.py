# -*- coding: utf-8 -*-
import sys
sys.path.append('C:\\Users\\Admin\\DockerFL\\n8n-selenium-bridge')
from Tools.TiktokScraper.tiktok_db import get_affiliate_connection

def create_table():
    conn = None
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.aff_video_templates (
                    id SERIAL PRIMARY KEY,
                    template_name VARCHAR(255) NOT NULL,
                    category VARCHAR(100),
                    gender VARCHAR(50), 
                    product_type_id INTEGER REFERENCES public.aff_product_types(id),
                    style_slug VARCHAR(100), 
                    is_active BOOLEAN DEFAULT true,
                    is_default BOOLEAN DEFAULT false,
                    shots_json JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("DONE!")
    except Exception as e:
        print("ERR: " + str(e))
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    create_table()
