# -*- coding: utf-8 -*-
import sys
sys.path.append('C:\\Users\\Admin\\DockerFL\\n8n-selenium-bridge')
from Tools.TiktokScraper.tiktok_db import get_affiliate_connection

def alter_columns():
    conn = None
    try:
        conn = get_affiliate_connection()
        conn.autocommit = True  # COMMIT TỪTNG LỆNH ĐỘC LẬP
        with conn.cursor() as cur:
            queries = [
                "ALTER TABLE public.aff_product_analysis ALTER COLUMN pain_point TYPE text;",
                "ALTER TABLE public.aff_product_analysis ALTER COLUMN suggested_hook TYPE text;",
                "ALTER TABLE public.aff_product_analysis ALTER COLUMN music_vibe TYPE text;",
                "ALTER TABLE public.aff_product_analysis ALTER COLUMN crop_coords TYPE varchar(255);",
                "ALTER TABLE public.aff_product_analysis ALTER COLUMN gender TYPE varchar(100);"
            ]
            for q in queries:
                try:
                    cur.execute(q)
                    print("OK: " + q)
                except Exception as e:
                    print("SKIPPED: " + str(e))
            
            print("DONE!")
    except Exception as e:
        print("ERR: " + str(e))
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    alter_columns()
