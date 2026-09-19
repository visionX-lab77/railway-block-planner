import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Local PostgreSQL
local_conn = psycopg2.connect(
    host="localhost",
    port="5408",
    database="railway_block_planner",
    user="postgres",
    password="hackthon"
)

# Neon PostgreSQL
neon_conn = psycopg2.connect(
    os.getenv("DATABASE_URL")
)

local_cur = local_conn.cursor()
neon_cur = neon_conn.cursor()

print("Connected to both databases!")

# Get local tables
local_cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
""")

tables = [row[0] for row in local_cur.fetchall()]

print("\nTables found:")
for table in tables:
    print("-", table)

for table in tables:
    print(f"\nMigrating: {table}")

    # Get column definitions
    local_cur.execute("""
        SELECT
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = %s
        ORDER BY ordinal_position;
    """, (table,))

    columns = local_cur.fetchall()

    column_defs = []

    for col in columns:
        name, data_type, char_len, precision, scale = col

        if data_type == "character varying":
            if char_len:
                sql_type = f"VARCHAR({char_len})"
            else:
                sql_type = "VARCHAR"
        elif data_type == "numeric":
            if precision and scale is not None:
                sql_type = f"NUMERIC({precision},{scale})"
            elif precision:
                sql_type = f"NUMERIC({precision})"
            else:
                sql_type = "NUMERIC"
        elif data_type == "integer":
            sql_type = "INTEGER"
        elif data_type == "bigint":
            sql_type = "BIGINT"
        elif data_type == "date":
            sql_type = "DATE"
        elif data_type == "time without time zone":
            sql_type = "TIME"
        elif data_type == "timestamp without time zone":
            sql_type = "TIMESTAMP"
        elif data_type == "boolean":
            sql_type = "BOOLEAN"
        elif data_type == "double precision":
            sql_type = "DOUBLE PRECISION"
        else:
            sql_type = data_type.upper()

        column_defs.append(f'"{name}" {sql_type}')

    create_sql = f'''
        CREATE TABLE IF NOT EXISTS "{table}" (
            {", ".join(column_defs)}
        );
    '''

    neon_cur.execute(create_sql)

    # Get data
    local_cur.execute(f'SELECT * FROM "{table}"')
    rows = local_cur.fetchall()

    if rows:
        column_names = [col[0] for col in columns]

        placeholders = ", ".join(["%s"] * len(column_names))
        column_list = ", ".join([f'"{c}"' for c in column_names])

        insert_sql = f'''
            INSERT INTO "{table}" ({column_list})
            VALUES ({placeholders})
        '''

        for row in rows:
            neon_cur.execute(insert_sql, row)

    print(f"  ✓ {len(rows)} rows migrated")

neon_conn.commit()

local_cur.close()
neon_cur.close()

local_conn.close()
neon_conn.close()

print("\n================================")
print("MIGRATION SUCCESSFUL!")
print("================================")