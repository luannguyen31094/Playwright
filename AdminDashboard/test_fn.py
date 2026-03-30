import psycopg2
conn=psycopg2.connect(host='127.0.0.1', database='automation', user='n8nuser', password='Luannguyen31094')
cur=conn.cursor()
try:
    cur.execute("SELECT * FROM public.fnc_get_product_web('', '', '', '', '')")
    print(cur.fetchone()[0][:100] if cur.rowcount > 0 else 'None')
except Exception as e:
    print(e)
