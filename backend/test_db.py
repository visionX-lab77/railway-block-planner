import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port="5408",
    database="railway_block_planner",
    user="postgres",
    password="hackthon"
)

print("Database connected successfully!")

conn.close()