from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import sys
import psycopg2
import pandas as pd
import io
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Railway AI Block Planner",
    description="AI-powered automatic block planning system for Indian Railways"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    return psycopg2.connect(
        os.getenv("DATABASE_URL")
    )
print("DATABASE_URL loaded:", bool(os.getenv("DATABASE_URL")))

# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "message": "Railway AI Block Planner API is running successfully!"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "OK"
    }


# =========================================================
# MAINTENANCE DATA
# =========================================================

@app.get("/maintenance")
def get_maintenance():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            record_id,
            asset_id,
            department,
            failure_risk_pct,
            condition_score,
            open_work_orders,
            ai_priority_score,
            ai_priority
        FROM ai_priority_results
        ORDER BY ai_priority_score DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "total_records": len(rows),
        "data": [
            {
                "record_id": row[0],
                "asset_id": row[1],
                "department": row[2],
                "failure_risk_pct": float(row[3]),
                "condition_score": float(row[4]),
                "open_work_orders": row[5],
                "ai_priority_score": float(row[6]),
                "ai_priority": row[7]
            }
            for row in rows
        ]
    }


# =========================================================
# BLOCK AVAILABILITY
# =========================================================

@app.get("/blocks")
def get_blocks():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            block_id,
            corridor,
            block_date,
            start_time,
            end_time,
            available_hours,
            status
        FROM block_availability
        ORDER BY block_date, start_time
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "total_blocks": len(rows),
        "data": [
            {
                "block_id": row[0],
                "corridor": row[1],
                "block_date": str(row[2]),
                "start_time": str(row[3]),
                "end_time": str(row[4]),
                "available_hours": float(row[5]),
                "status": row[6]
            }
            for row in rows
        ]
    }


# =========================================================
# WEEKLY PLAN
# =========================================================

@app.get("/weekly-plan")
def get_weekly_plan():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            block_id,
            block_date,
            corridor,
            start_time,
            end_time,
            record_id,
            asset_id,
            department,
            maintenance_duration_minutes,
            ai_priority,
            ai_priority_score
        FROM weekly_block_plan
        ORDER BY block_date, start_time
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "total_tasks": len(rows),
        "data": [
            {
                "block_id": row[0],
                "block_date": str(row[1]),
                "corridor": row[2],
                "start_time": str(row[3]),
                "end_time": str(row[4]),
                "record_id": row[5],
                "asset_id": row[6],
                "department": row[7],
                "maintenance_duration_minutes": row[8],
                "ai_priority": row[9],
                "ai_priority_score": float(row[10])
            }
            for row in rows
        ]
    }


# =========================================================
# GENERATE WEEKLY PLAN
# =========================================================

@app.post("/generate-plan")
def generate_plan():

    try:

        result = subprocess.run(
            [
                sys.executable,
                r"C:\Users\vigne\Desktop\hackthon\backend\ai\optimization\weekly_optimizer.py"
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            return {
                "message": "Plan generation failed",
                "error": result.stderr
            }

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                block_id,
                block_date,
                corridor,
                start_time,
                end_time,
                record_id,
                asset_id,
                department,
                maintenance_duration_minutes,
                ai_priority,
                ai_priority_score
            FROM weekly_block_plan
            ORDER BY block_date, start_time
        """)

        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "message": "Optimized plan generated successfully",
            "total_tasks": len(rows),
            "data": [
                {
                    "block_id": row[0],
                    "block_date": str(row[1]),
                    "corridor": row[2],
                    "start_time": str(row[3]),
                    "end_time": str(row[4]),
                    "record_id": row[5],
                    "asset_id": row[6],
                    "department": row[7],
                    "maintenance_duration_minutes": row[8],
                    "ai_priority": row[9],
                    "ai_priority_score": float(row[10])
                }
                for row in rows
            ]
        }

    except Exception as e:

        return {
            "message": "Plan generation failed",
            "error": str(e)
        }


# =========================================================
# MONTHLY PLAN
# =========================================================

@app.get("/monthly-plan")
def get_monthly_plan():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            block_id,
            block_date,
            corridor,
            start_time,
            end_time,
            record_id,
            asset_id,
            department,
            maintenance_duration_minutes,
            ai_priority,
            ai_priority_score
        FROM monthly_block_plan
        ORDER BY block_date, start_time
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "total_tasks": len(rows),
        "data": [
            {
                "block_id": row[0],
                "block_date": str(row[1]),
                "corridor": row[2],
                "start_time": str(row[3]),
                "end_time": str(row[4]),
                "record_id": row[5],
                "asset_id": row[6],
                "department": row[7],
                "maintenance_duration_minutes": row[8],
                "ai_priority": row[9],
                "ai_priority_score": float(row[10])
            }
            for row in rows
        ]
    }


# =========================================================
# GENERATE MONTHLY PLAN
# =========================================================

@app.post("/generate-monthly-plan")
def generate_monthly_plan():

    try:

        result = subprocess.run(
            [
                sys.executable,
                r"C:\Users\vigne\Desktop\hackthon\backend\ai\optimization\monthly_optimizer.py"
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            return {
                "message": "Monthly plan generation failed",
                "error": result.stderr
            }

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                block_id,
                block_date,
                corridor,
                start_time,
                end_time,
                record_id,
                asset_id,
                department,
                maintenance_duration_minutes,
                ai_priority,
                ai_priority_score
            FROM monthly_block_plan
            ORDER BY block_date, start_time
        """)

        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "message": "Monthly plan generated successfully",
            "total_tasks": len(rows),
            "data": [
                {
                    "block_id": row[0],
                    "block_date": str(row[1]),
                    "corridor": row[2],
                    "start_time": str(row[3]),
                    "end_time": str(row[4]),
                    "record_id": row[5],
                    "asset_id": row[6],
                    "department": row[7],
                    "maintenance_duration_minutes": row[8],
                    "ai_priority": row[9],
                    "ai_priority_score": float(row[10])
                }
                for row in rows
            ]
        }

    except Exception as e:

        return {
            "message": "Monthly plan generation failed",
            "error": str(e)
        }


# =========================================================
# UPLOAD MAINTENANCE DATA
# =========================================================

@app.post("/upload-maintenance-data")
async def upload_maintenance_data(
    department: str = Form(...),
    file: UploadFile = File(...)
):

    try:

        # -------------------------------------------------
        # Check Department
        # -------------------------------------------------

        department = department.upper().strip()

        if department not in ["TMS", "SMMS", "TDMS"]:

            return {
                "success": False,
                "message": "Invalid department. Select TMS, SMMS or TDMS."
            }


        # -------------------------------------------------
        # Check File Type
        # -------------------------------------------------

        filename = file.filename.lower()

        if not (
            filename.endswith(".csv")
            or filename.endswith(".xlsx")
            or filename.endswith(".xls")
        ):

            return {
                "success": False,
                "message": "Only CSV or Excel files are supported."
            }


        # -------------------------------------------------
        # Read Uploaded File
        # -------------------------------------------------

        file_content = await file.read()

        if filename.endswith(".csv"):

            df = pd.read_csv(io.BytesIO(file_content))

        else:

            df = pd.read_excel(io.BytesIO(file_content))


        # -------------------------------------------------
        # Clean Column Names
        # -------------------------------------------------

        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace("-", "_")
        )


        # -------------------------------------------------
        # Handle Possible Column Name Variations
        # -------------------------------------------------

        column_mapping = {

            "failure_risk": "failure_risk_pct",
            "failure_risk_percent": "failure_risk_pct",
            "failure_risk_%": "failure_risk_pct",

            "condition": "condition_score",

            "open_work_orders_count": "open_work_orders",
            "work_orders": "open_work_orders",

            "operating_hour": "operating_hours",
            "operating_hrs": "operating_hours",

            "data_status": "data_status"
        }

        df.rename(columns=column_mapping, inplace=True)


        # -------------------------------------------------
        # Required Columns
        # -------------------------------------------------

        required_columns = [
            "record_id",
            "asset_id",
            "inspection_date",
            "operating_hours",
            "failure_risk_pct",
            "condition_score",
            "open_work_orders"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:

            return {
                "success": False,
                "message": "Missing required columns.",
                "missing_columns": missing_columns
            }


        # -------------------------------------------------
        # Add Department
        # -------------------------------------------------

        df["department"] = department


        # -------------------------------------------------
        # Data Cleaning
        # -------------------------------------------------

        df["inspection_date"] = pd.to_datetime(
            df["inspection_date"],
            errors="coerce"
        ).dt.date

        df["operating_hours"] = pd.to_numeric(
            df["operating_hours"],
            errors="coerce"
        ).fillna(0)

        df["failure_risk_pct"] = pd.to_numeric(
            df["failure_risk_pct"],
            errors="coerce"
        ).fillna(0)

        df["condition_score"] = pd.to_numeric(
            df["condition_score"],
            errors="coerce"
        ).fillna(0)

        df["open_work_orders"] = pd.to_numeric(
            df["open_work_orders"],
            errors="coerce"
        ).fillna(0).astype(int)


        # -------------------------------------------------
        # Data Status
        # -------------------------------------------------

        if "data_status" not in df.columns:

            df["data_status"] = "UPLOADED"


        # -------------------------------------------------
        # Select Database Table
        # -------------------------------------------------

        table_map = {

            "TMS": "tms_maintenance",
            "SMMS": "smms_maintenance",
            "TDMS": "tdms_maintenance"

        }

        table_name = table_map[department]


        # -------------------------------------------------
        # Insert Into PostgreSQL
        # -------------------------------------------------

        conn = get_connection()
        cursor = conn.cursor()


        # Delete previous uploaded rows
        # This keeps the prototype database clean.

        cursor.execute(
            f"DELETE FROM {table_name}"
        )


        # Insert new data

        insert_query = f"""
            INSERT INTO {table_name}
            (
                record_id,
                asset_id,
                inspection_date,
                operating_hours,
                failure_risk_pct,
                condition_score,
                open_work_orders,
                priority,
                data_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """


        for _, row in df.iterrows():

            priority_value = (
                str(row["priority"])
                if "priority" in df.columns
                else "UPLOADED"
            )

            cursor.execute(
                insert_query,
                (
                    str(row["record_id"]),
                    str(row["asset_id"]),
                    row["inspection_date"],
                    float(row["operating_hours"]),
                    float(row["failure_risk_pct"]),
                    float(row["condition_score"]),
                    int(row["open_work_orders"]),
                    priority_value,
                    str(row["data_status"])
                )
            )


        conn.commit()

        cursor.close()
        conn.close()


        # -------------------------------------------------
        # RUN AI PRIORITY ENGINE
        # -------------------------------------------------

        ai_result = subprocess.run(
            [
                sys.executable,
                r"C:\Users\vigne\Desktop\hackthon\backend\ai\priority_engine.py"
            ],
            capture_output=True,
            text=True
        )


        if ai_result.returncode != 0:

            return {
                "success": False,
                "message": "Data uploaded, but AI priority calculation failed.",
                "error": ai_result.stderr
            }


        # -------------------------------------------------
        # SUCCESS RESPONSE
        # -------------------------------------------------

        return {

            "success": True,

            "message": (
                f"{department} maintenance data uploaded successfully "
                f"and AI priority updated."
            ),

            "department": department,

            "filename": file.filename,

            "records_uploaded": len(df)

        }


    except Exception as e:

        return {

            "success": False,

            "message": "Upload failed",

            "error": str(e)

        }