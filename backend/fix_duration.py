import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port="5408",
    database="railway_block_planner",
    user="postgres",
    password="hackthon"
)

cur = conn.cursor()

cur.execute("""
UPDATE ai_priority_results
SET maintenance_duration_minutes =
    CASE
        WHEN department = 'TMS' THEN 40
        WHEN department = 'SMMS' THEN 30
        WHEN department = 'TDMS' THEN 50
    END
WHERE maintenance_duration_minutes IS NULL;
""")

conn.commit()

print("Missing durations fixed:", cur.rowcount)

cur.close()
conn.close()