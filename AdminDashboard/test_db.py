import psycopg2
conn = psycopg2.connect("host=127.0.0.1 dbname=automation user=n8nuser password=Luannguyen31094 port=5432")
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='v_product_ranking'")
print("Columns for v_product_ranking:")
for r in cur.fetchall():
    print(r)
