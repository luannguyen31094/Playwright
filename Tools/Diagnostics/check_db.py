
import psycopg2
import sys

# Ép ra UTF-8 để CMD không lỗi khi gặp ký tự lạ
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect("dbname=automation user=n8nuser password=Luannguyen31094 host=localhost")
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'aff_shops';")
# print("aff_shops columns:", cur.fetchall())

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'aff_product_analysis';")
# print("aff_product_analysis columns:", cur.fetchall())

