from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pymysql
import json
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "root",  # change if different
    "database": "ml_experiment_tracker",
    "cursorclass": pymysql.cursors.DictCursor
}

def get_connection():
    return pymysql.connect(**db_config)

@app.get("/")
def home():
    return {"message": "ML Experiment Tracker API running"}

# --------------------------------------------------------------------
# Create Experiment
# --------------------------------------------------------------------
@app.post("/create_experiment")
def create_experiment(payload: dict):
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO Experiment (experiment_name, model_type, hyperparameters, accuracy, loss, description, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'created')
            """
            cur.execute(sql, (
                payload.get("experiment_name"),
                payload.get("model_type"),
                json.dumps(payload.get("hyperparameters")),
                payload.get("accuracy"),
                payload.get("loss"),
                payload.get("description")
            ))
            conn.commit()
            return {"message": "Experiment created successfully", "experiment_id": cur.lastrowid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# --------------------------------------------------------------------
# Get Experiments
# --------------------------------------------------------------------
@app.get("/experiments")
def get_experiments():
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM Experiment ORDER BY created_at DESC")
            results = cur.fetchall()
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# --------------------------------------------------------------------
# Detect Contamination
# --------------------------------------------------------------------
@app.post("/detect_contamination")
def detect_contamination(payload: dict):
    exper_id = payload.get("exper_id")
    train_dataset_id = payload.get("train_dataset_id")
    test_dataset_id = payload.get("test_dataset_id")

    if not exper_id or not train_dataset_id or not test_dataset_id:
        raise HTTPException(status_code=400, detail="Missing required fields")

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # 1. Create a contamination report record first
            insert_report = """
                INSERT INTO Contamination_Report (
                    exper_id, generated_at, contaminated_rows_count, contamination_percentage, status
                ) VALUES (%s, NOW(), 0, 0, 'pending')
            """
            cur.execute(insert_report, (exper_id,))
            report_id = cur.lastrowid

            # 2. Generate missing hashes
            cur.execute("CALL generate_and_store_hashes(%s)", (train_dataset_id,))
            cur.execute("CALL generate_and_store_hashes(%s)", (test_dataset_id,))

            # 3. Run contamination detection
            cur.execute("CALL detect_exact_duplicates(%s, %s, %s)", (train_dataset_id, test_dataset_id, report_id))

            # 4. Fetch contamination count
            cur.execute("SELECT COUNT(*) AS contaminated_rows FROM Contaminated_Row WHERE report_id = %s", (report_id,))
            contaminated_rows = cur.fetchone()["contaminated_rows"]

            # 5. Get total test rows for percentage
            cur.execute("SELECT COUNT(*) AS total_rows FROM Data_Row WHERE dataset_id = %s", (test_dataset_id,))
            total_rows = cur.fetchone()["total_rows"]

            contamination_percentage = round((contaminated_rows / total_rows) * 100, 2) if total_rows > 0 else 0

            # 6. Update the report with final results
            update_report = """
                UPDATE Contamination_Report
                SET contaminated_rows_count = %s,
                    contamination_percentage = %s,
                    status = 'completed'
                WHERE report_id = %s
            """
            cur.execute(update_report, (contaminated_rows, contamination_percentage, report_id))
            conn.commit()

            return {
                "message": "Contamination detection completed",
                "experiment_id": exper_id,
                "report_id": report_id,
                "contaminated_rows": contaminated_rows,
                "contamination_percentage": contamination_percentage
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contamination detection failed: {e}")
    finally:
        conn.close()

# --------------------------------------------------------------------
# View Dataset Health
# --------------------------------------------------------------------
@app.get("/dataset_health")
def get_dataset_health():
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM dataset_health_check")
            results = cur.fetchall()
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
