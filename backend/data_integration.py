import pandas as pd
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port="5408",
    database="railway_block_planner",
    user="postgres",
    password="hackthon"
)

tms = pd.read_sql("SELECT * FROM tms_maintenance", conn)
smms = pd.read_sql("SELECT * FROM smms_maintenance", conn)
tdms = pd.read_sql("SELECT * FROM tdms_maintenance", conn)

tms["department"] = "TMS"
smms["department"] = "SMMS"
tdms["department"] = "TDMS"

combined = pd.concat(
    [tms, smms, tdms],
    ignore_index=True
)

print("================================")
print("DATA INTEGRATION SUCCESSFUL")
print("================================")

print("TMS   :", len(tms))
print("SMMS  :", len(smms))
print("TDMS  :", len(tdms))
print("TOTAL :", len(combined))

print("\nCombined Data:")
print(combined.head(10))

conn.close()