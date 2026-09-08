import pandas as pd
import psycopg2


# =========================================================
# DATABASE CONNECTION
# =========================================================

conn = psycopg2.connect(
    host="localhost",
    port="5408",
    database="railway_block_planner",
    user="postgres",
    password="hackthon"
)


# =========================================================
# READ MAINTENANCE DATA
# =========================================================

tms = pd.read_sql(
    "SELECT * FROM tms_maintenance",
    conn
)

smms = pd.read_sql(
    "SELECT * FROM smms_maintenance",
    conn
)

tdms = pd.read_sql(
    "SELECT * FROM tdms_maintenance",
    conn
)


# =========================================================
# ADD DEPARTMENT
# =========================================================

tms["department"] = "TMS"
smms["department"] = "SMMS"
tdms["department"] = "TDMS"


# =========================================================
# COMBINE ALL DEPARTMENTS
# =========================================================

data = pd.concat(
    [tms, smms, tdms],
    ignore_index=True
)


# =========================================================
# CONVERT REQUIRED COLUMNS
# =========================================================

data["failure_risk_pct"] = pd.to_numeric(
    data["failure_risk_pct"],
    errors="coerce"
).fillna(0)

data["condition_score"] = pd.to_numeric(
    data["condition_score"],
    errors="coerce"
).fillna(0)

data["open_work_orders"] = pd.to_numeric(
    data["open_work_orders"],
    errors="coerce"
).fillna(0)

data["operating_hours"] = pd.to_numeric(
    data["operating_hours"],
    errors="coerce"
).fillna(0)


# =========================================================
# AI PRIORITY SCORE
# =========================================================

max_operating_hours = data["operating_hours"].max()

if max_operating_hours > 0:

    operating_hours_score = (
        data["operating_hours"]
        / max_operating_hours
    ) * 100

else:

    operating_hours_score = 0


data["ai_priority_score"] = (
    data["failure_risk_pct"] * 0.40
    + (100 - data["condition_score"]) * 0.30
    + data["open_work_orders"] * 5 * 0.20
    + operating_hours_score * 0.10
)


# =========================================================
# PRIORITY CATEGORY
# =========================================================

def get_priority(score):

    if score >= 75:
        return "CRITICAL"

    elif score >= 50:
        return "HIGH"

    elif score >= 25:
        return "MEDIUM"

    else:
        return "LOW"


data["ai_priority"] = (
    data["ai_priority_score"]
    .apply(get_priority)
)


# =========================================================
# SORT HIGHEST PRIORITY FIRST
# =========================================================

data = data.sort_values(
    by="ai_priority_score",
    ascending=False
)


# =========================================================
# CLEAR OLD AI RESULTS
# =========================================================
# IMPORTANT:
# Prevents duplicate records after every upload.

cursor = conn.cursor()

cursor.execute(
    "DELETE FROM ai_priority_results"
)

conn.commit()

print("Old AI priority results cleared.")


# =========================================================
# SAVE NEW AI RESULTS
# =========================================================

for _, row in data.iterrows():

    cursor.execute(
        """
        INSERT INTO ai_priority_results
        (
            record_id,
            asset_id,
            department,
            failure_risk_pct,
            condition_score,
            open_work_orders,
            operating_hours,
            ai_priority_score,
            ai_priority
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            row["record_id"],
            row["asset_id"],
            row["department"],
            row["failure_risk_pct"],
            row["condition_score"],
            row["open_work_orders"],
            row["operating_hours"],
            row["ai_priority_score"],
            row["ai_priority"]
        )
    )


conn.commit()


# =========================================================
# SUCCESS MESSAGE
# =========================================================

print("\nAI results saved to PostgreSQL successfully!")

print("================================")
print("AI PRIORITY ENGINE SUCCESSFUL")
print("================================")

print(
    "TMS records:",
    len(tms)
)

print(
    "SMMS records:",
    len(smms)
)

print(
    "TDMS records:",
    len(tdms)
)

print(
    "Total records:",
    len(data)
)


# =========================================================
# TOP 10 PRIORITIES
# =========================================================

print("\nTop 10 Maintenance Priorities:")

print(
    data[
        [
            "record_id",
            "asset_id",
            "department",
            "failure_risk_pct",
            "condition_score",
            "open_work_orders",
            "ai_priority_score",
            "ai_priority"
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# =========================================================
# CLOSE CONNECTION
# =========================================================

cursor.close()
conn.close()