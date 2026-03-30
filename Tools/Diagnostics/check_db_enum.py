import psycopg2
conn = psycopg2.connect("dbname=affiliate user=n8nuser password=Luannguyen31094 host=localhost")
cur = conn.cursor()
cur.execute("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'campaign_status'::regtype;")
print("enum values for campaign_status:", [r[0] for r in cur.fetchall()])
