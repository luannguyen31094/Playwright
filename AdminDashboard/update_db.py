import psycopg2
conn = psycopg2.connect(host='127.0.0.1', database='automation', user='n8nuser', password='Luannguyen31094')
cur = conn.cursor()
sql = """
CREATE OR REPLACE FUNCTION public.fnc_get_product_web(
    categoryid text, 
    final_rank text, 
    todate text, 
    fromdate text, 
    statusvideo text)
RETURNS TABLE(data json)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN query
    SELECT json_agg(r.*)
    FROM 
    (
        SELECT v.*, p.shop_id, p.canonical_url, c.name_vi as category 
        FROM v_product_ranking v
        LEFT JOIN aff_products p ON v.tiktok_product_id = p.tiktok_product_id
        LEFT JOIN aff_categories c ON p.category_id = c.id
        WHERE 
            (fnc_get_product_web.categoryid = '' OR c.name_vi ILIKE '%' || fnc_get_product_web.categoryid || '%' OR c.id::text = fnc_get_product_web.categoryid) AND
            (fnc_get_product_web.final_rank = '' OR v.final_rank = fnc_get_product_web.final_rank) AND
            (fnc_get_product_web.fromdate = '' OR v.captured_at >= fnc_get_product_web.fromdate::timestamp) AND
            (fnc_get_product_web.todate = '' OR v.captured_at <= fnc_get_product_web.todate::timestamp + interval '1 day') AND
            (fnc_get_product_web.statusvideo = '' OR v.status = fnc_get_product_web.statusvideo)
        ORDER BY v.total_hard_score DESC NULLS LAST LIMIT 500
    ) r;
END;
$$;
"""
cur.execute(sql)
conn.commit()
print('Function created successfully!')
