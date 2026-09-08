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
# LOAD BLOCKS
# ==============================

blocks = pd.read_sql("""
    SELECT *
    FROM block_availability
    WHERE status = 'AVAILABLE'
    ORDER BY start_time
""", conn)

# ==============================
# LOAD TRAINS
# ==============================

trains = pd.read_sql("""
    SELECT *
    FROM train_timetable
    ORDER BY arrival_time
""", conn)

conn.close()

print("Maintenance tasks:", len(maintenance))
print("Available blocks:", len(blocks))
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

# Each task can be assigned to a block

for i in range(len(maintenance)):

    for j in valid_blocks:

        task_corridor = maintenance.iloc[i]["corridor"]
        block_corridor = blocks.loc[j]["corridor"]

        duration = int(
            maintenance.iloc[i]["maintenance_duration_minutes"]
        )

        block_duration = get_block_duration(
            blocks.loc[j]["start_time"],
            blocks.loc[j]["end_time"]
        )

        # Only compatible tasks can use the block

        if (
            task_corridor == block_corridor
            and duration <= block_duration
        ):

            assignments[i, j] = model.NewBoolVar(
                f"task_{i}_block_{j}"
            )


# ==============================
# ONE TASK CAN USE ONLY ONE BLOCK
# ==============================

for i in range(len(maintenance)):

    task_variables = [
        assignments[i, j]
        for j in valid_blocks
        if (i, j) in assignments
    ]

    if task_variables:
        model.Add(sum(task_variables) <= 1)


# ==============================
# BLOCK DURATION CONSTRAINT
# ==============================

for j in valid_blocks:

    block_variables = []

    for i in range(len(maintenance)):

        if (i, j) in assignments:
            block_variables.append(
                assignments[i, j]
            )

    if block_variables:

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

        block_duration = get_block_duration(
            blocks.loc[j]["start_time"],
            blocks.loc[j]["end_time"]
        )

        model.Add(
            sum(durations) <= block_duration
        )


# ==============================
# MAXIMIZE PRIORITY SCORE
# ==============================

objective_terms = []

for (i, j), variable in assignments.items():

    priority_score = float(
        maintenance.iloc[i]["ai_priority_score"]
    )

    objective_terms.append(
        int(priority_score * 100) * variable
    )

model.Maximize(sum(objective_terms))


# ==============================
# SOLVE
# ==============================

solver = cp_model.CpSolver()

status = solver.Solve(model)


# ==============================
# RESULT
# ==============================

print("\n==========================================")
print("AI + TRAIN AWARE BLOCK OPTIMIZATION")
print("==========================================")

if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:

    assigned_tasks = 0

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
                f"\n{block['block_id']} "
                f"({block['start_time']} - {block['end_time']})"
            )

            for task in selected_tasks:

                print(
                    f"   -> {task['record_id']} "
                    f"({task['department']}) "
                    f"- {task['maintenance_duration_minutes']} min "
                    f"- {task['ai_priority']}"
                )

                assigned_tasks += 1

            print(
                f"   Total maintenance time: "
                f"{total_duration} minutes"
            )

    print("\n==========================================")
    print("TOTAL TASKS ASSIGNED:", assigned_tasks)
    print("==========================================")

else:

    print("No feasible solution found.")