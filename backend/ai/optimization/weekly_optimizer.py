import pandas as pd
import psycopg2
from ortools.sat.python import cp_model

# ==============================
# DATABASE CONNECTION
# ==============================

conn = psycopg2.connect(
    host="localhost",
    port="5408",
    database="railway_block_planner",
    user="postgres",
    password="hackthon"
)

# ==============================
# LOAD MAINTENANCE TASKS
# ==============================

maintenance = pd.read_sql("""
    SELECT *
    FROM ai_priority_results
    WHERE ai_priority IN ('CRITICAL', 'HIGH')
    ORDER BY ai_priority_score DESC
    LIMIT 20
""", conn)

# ==============================
# LOAD WEEKLY BLOCKS
# ==============================

blocks = pd.read_sql("""
    SELECT *
    FROM block_availability
    WHERE status = 'AVAILABLE'
      AND block_date BETWEEN '2026-09-07' AND '2026-09-13'
    ORDER BY block_date, start_time
""", conn)

# ==============================
# LOAD TRAIN TIMETABLE
# ==============================

trains = pd.read_sql("""
    SELECT *
    FROM train_timetable
    ORDER BY arrival_time
""", conn)

print("================================")
print("WEEKLY BLOCK PLANNER")
print("================================")

print("Maintenance tasks:", len(maintenance))
print("Weekly blocks:", len(blocks))
print("Train services:", len(trains))


# ==============================
# TRAIN CONFLICT CHECK
# ==============================

def has_train_conflict(block_start, block_end, trains):

    for _, train in trains.iterrows():

        if (
            block_start < train["departure_time"]
            and block_end > train["arrival_time"]
        ):
            return True

    return False


# ==============================
# BLOCK DURATION
# ==============================

def get_block_duration(start_time, end_time):

    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute

    return end_minutes - start_minutes


# ==============================
# FIND VALID BLOCKS
# ==============================

valid_blocks = []

for j, block in blocks.iterrows():

    if not has_train_conflict(
        block["start_time"],
        block["end_time"],
        trains
    ):

        valid_blocks.append(j)

print("Conflict-free blocks:", len(valid_blocks))


# ==============================
# OR-TOOLS MODEL
# ==============================

model = cp_model.CpModel()

assignments = {}

for i in range(len(maintenance)):

    for j in valid_blocks:

        task = maintenance.iloc[i]
        block = blocks.loc[j]

        task_corridor = task["corridor"]
        block_corridor = block["corridor"]

        task_duration = int(
            task["maintenance_duration_minutes"]
        )

        block_duration = get_block_duration(
            block["start_time"],
            block["end_time"]
        )

        # Compatible task + block

        if (
            task_corridor == block_corridor
            and task_duration <= block_duration
        ):

            assignments[i, j] = model.NewBoolVar(
                f"task_{i}_block_{j}"
            )


# ==============================
# ONE TASK → ONE BLOCK
# ==============================

for i in range(len(maintenance)):

    variables = [
        assignments[i, j]
        for j in valid_blocks
        if (i, j) in assignments
    ]

    if variables:
        model.Add(sum(variables) <= 1)


# ==============================
# BLOCK CAPACITY
# ==============================

for j in valid_blocks:

    durations = []

    for i in range(len(maintenance)):

        if (i, j) in assignments:

            duration = int(
                maintenance.iloc[i][
                    "maintenance_duration_minutes"
                ]
            )

            durations.append(
                duration * assignments[i, j]
            )

    if durations:

        block_duration = get_block_duration(
            blocks.loc[j]["start_time"],
            blocks.loc[j]["end_time"]
        )

        model.Add(
            sum(durations) <= block_duration
        )


# ==============================
# MAXIMIZE AI PRIORITY
# ==============================

objective = []

for (i, j), variable in assignments.items():

    score = float(
        maintenance.iloc[i]["ai_priority_score"]
    )

    objective.append(
        int(score * 100) * variable
    )

model.Maximize(sum(objective))


# ==============================
# SOLVE
# ==============================

solver = cp_model.CpSolver()

status = solver.Solve(model)


# ==============================
# SAVE RESULTS
# ==============================

cursor = conn.cursor()
cursor.execute("DELETE FROM weekly_block_plan")
conn.commit()

print("\n================================")
print("WEEKLY PLAN RESULT")
print("================================")

if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:

    assigned = 0

    for j in valid_blocks:

        block = blocks.loc[j]

        selected_tasks = []

        total_duration = 0

        for i in range(len(maintenance)):

            if (i, j) in assignments:

                if solver.Value(assignments[i, j]) == 1:

                    task = maintenance.iloc[i]

                    selected_tasks.append(task)

                    total_duration += int(
                        task["maintenance_duration_minutes"]
                    )

        if selected_tasks:

            print(
                f"\n{block['block_date']} | "
                f"{block['block_id']} | "
                f"{block['start_time']} - "
                f"{block['end_time']}"
            )

            for task in selected_tasks:

                print(
                    f"   -> {task['record_id']} | "
                    f"{task['department']} | "
                    f"{task['ai_priority']} | "
                    f"{task['maintenance_duration_minutes']} min"
                )

                cursor.execute(
                    """
                    INSERT INTO weekly_block_plan
                    (
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
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        block["block_id"],
                        block["block_date"],
                        block["corridor"],
                        block["start_time"],
                        block["end_time"],
                        task["record_id"],
                        task["asset_id"],
                        task["department"],
                        int(task["maintenance_duration_minutes"]),
                        task["ai_priority"],
                        float(task["ai_priority_score"])
                    )
                )

                assigned += 1

            print(
                f"   Total maintenance time: "
                f"{total_duration} minutes"
            )

    conn.commit()

    print("\n================================")
    print("WEEKLY PLAN SAVED SUCCESSFULLY")
    print("================================")
    print("Total tasks assigned:", assigned)

else:

    print("No feasible weekly plan found.")

conn.close()