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
# LOAD MAINTENANCE DATA
# ==============================

maintenance = pd.read_sql("""
    SELECT *
    FROM ai_priority_results
    WHERE ai_priority IN ('CRITICAL', 'HIGH')
    ORDER BY ai_priority_score DESC
    LIMIT 50
""", conn)

maintenance["corridor"] = (
    maintenance["corridor"]
    .fillna("R001")
    .astype(str)
    .str.strip()
    .str.upper()
)

# ==============================
# LOAD AVAILABLE BLOCKS
# ==============================

blocks = pd.read_sql("""
    SELECT *
    FROM block_availability
    WHERE status = 'AVAILABLE'
    ORDER BY block_date, start_time
""", conn)

blocks["corridor"] = (
    blocks["corridor"]
    .fillna("R001")
    .astype(str)
    .str.strip()
    .str.upper()
)

# ==============================
# LOAD TRAIN TIMETABLE
# ==============================

trains = pd.read_sql("""
    SELECT *
    FROM train_timetable
    ORDER BY arrival_time
""", conn)

print("================================")
print("MONTHLY BLOCK PLANNER")
print("================================")

print("Maintenance tasks:", len(maintenance))
print("Available blocks:", len(blocks))
print("Train services:", len(trains))


# ==============================
# BLOCK DURATION
# ==============================

def get_block_duration(start_time, end_time):

    start_minutes = (
        start_time.hour * 60
        + start_time.minute
    )

    end_minutes = (
        end_time.hour * 60
        + end_time.minute
    )

    return end_minutes - start_minutes


# ==============================
# TRAIN CONFLICT CHECK
# ==============================

def has_train_conflict(
    block_start,
    block_end,
    trains
):

    for _, train in trains.iterrows():

        if (
            block_start < train["departure_time"]
            and
            block_end > train["arrival_time"]
        ):
            return True

    return False


# ==============================
# FIND CONFLICT-FREE BLOCKS
# ==============================

valid_blocks = []

for j, block in blocks.iterrows():

    if not has_train_conflict(
        block["start_time"],
        block["end_time"],
        trains
    ):

        valid_blocks.append(j)


print(
    "Conflict-free blocks:",
    len(valid_blocks)
)


# ==============================
# OR-TOOLS MODEL
# ==============================

model = cp_model.CpModel()

assignments = {}


# ==============================
# CREATE ASSIGNMENT VARIABLES
# ==============================

for i in range(len(maintenance)):

    task = maintenance.iloc[i]

    task_duration = int(
        task["maintenance_duration_minutes"]
    )

    for j in valid_blocks:

        block = blocks.loc[j]

        block_duration = get_block_duration(
            block["start_time"],
            block["end_time"]
        )

        if (
            task["corridor"] == block["corridor"]
            and
            task_duration <= block_duration
        ):

            assignments[i, j] = model.NewBoolVar(
                f"task_{i}_block_{j}"
            )


# ==================================================
# CONSTRAINT 1
# SAME RECORD CAN USE ONLY ONE BLOCK
# ==================================================

for i in range(len(maintenance)):

    variables = [
        assignments[i, j]
        for j in valid_blocks
        if (i, j) in assignments
    ]

    if variables:

        model.Add(
            sum(variables) <= 1
        )


# ==================================================
# CONSTRAINT 2
# SAME ASSET CAN BE SCHEDULED ONLY ONCE
# ==================================================

asset_groups = {}

for i in range(len(maintenance)):

    asset_id = maintenance.iloc[i]["asset_id"]

    if asset_id not in asset_groups:

        asset_groups[asset_id] = []

    asset_groups[asset_id].append(i)


for asset_id, task_indexes in asset_groups.items():

    variables = []

    for i in task_indexes:

        for j in valid_blocks:

            if (i, j) in assignments:

                variables.append(
                    assignments[i, j]
                )

    if variables:

        model.Add(
            sum(variables) <= 1
        )


# ==================================================
# CONSTRAINT 3
# BLOCK DURATION
# ==================================================

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
            sum(durations)
            <= block_duration
        )


# ==================================================
# OBJECTIVE
# MAXIMIZE AI PRIORITY SCORE
# ==================================================

objective = []

for (i, j), variable in assignments.items():

    score = float(
        maintenance.iloc[i][
            "ai_priority_score"
        ]
    )

    objective.append(
        int(score * 100) * variable
    )


if objective:

    model.Maximize(
        sum(objective)
    )


# ==============================
# SOLVE MODEL
# ==============================

solver = cp_model.CpSolver()

status = solver.Solve(model)


print("\n================================")
print("MONTHLY PLAN RESULT")
print("================================")


# ==============================
# DATABASE CURSOR
# ==============================

cursor = conn.cursor()


# ==============================
# DELETE OLD MONTHLY PLAN
# ==============================

cursor.execute(
    "DELETE FROM monthly_block_plan"
)

conn.commit()


# ==============================
# SAVE NEW PLAN
# ==============================

if status in [
    cp_model.OPTIMAL,
    cp_model.FEASIBLE
]:

    assigned = 0

    used_assets = set()

    for j in valid_blocks:

        block = blocks.loc[j]

        selected_tasks = []

        total_duration = 0


        for i in range(
            len(maintenance)
        ):

            if (i, j) in assignments:

                if solver.Value(
                    assignments[i, j]
                ) == 1:

                    task = maintenance.iloc[i]

                    asset_id = task["asset_id"]

                    # Extra safety check
                    if asset_id in used_assets:
                        continue

                    selected_tasks.append(
                        task
                    )

                    total_duration += int(
                        task[
                            "maintenance_duration_minutes"
                        ]
                    )

                    used_assets.add(
                        asset_id
                    )


        # ==============================
        # SAVE BLOCK TASKS
        # ==============================

        if selected_tasks:

            print(
                f"\n{block['block_date']} | "
                f"{block['block_id']} | "
                f"{block['start_time']} - "
                f"{block['end_time']}"
            )


            for task in selected_tasks:

                print(
                    f"   -> "
                    f"{task['record_id']} | "
                    f"{task['asset_id']} | "
                    f"{task['department']} | "
                    f"{task['ai_priority']} | "
                    f"{task['maintenance_duration_minutes']} min"
                )


                cursor.execute(
                    """
                    INSERT INTO monthly_block_plan
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
                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
                        int(
                            task[
                                "maintenance_duration_minutes"
                            ]
                        ),
                        task["ai_priority"],
                        float(
                            task[
                                "ai_priority_score"
                            ]
                        )
                    )
                )

                assigned += 1


            print(
                "   Total maintenance time:",
                total_duration,
                "minutes"
            )


    conn.commit()


    print("\n================================")
    print("MONTHLY PLAN SAVED SUCCESSFULLY")
    print("================================")

    print(
        "Total tasks assigned:",
        assigned
    )

    print(
        "Unique assets scheduled:",
        len(used_assets)
    )


else:

    print(
        "No feasible monthly plan found."
    )


# ==============================
# CLOSE DATABASE
# ==============================

cursor.close()
conn.close()