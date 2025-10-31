from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import JSONResponse
import pandas as pd
import os
from datetime import datetime
from db_config import get_connection

app = FastAPI(title="ML Experiment Tracker API")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(filepath, "wb") as f:
        f.write(await file.read())

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")

    conn = get_connection()

    cursor = conn.cursor(buffered=True)

    try:
        cursor.execute("""
            INSERT INTO Dataset (
                dataset_name, filepath, filename, file_format,
                dataset_type, description, filesize, checksum
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, SHA2(%s, 256))
        """, (
            file.filename,
            filepath,
            file.filename,
            "csv",
            "uploaded",
            "User uploaded dataset",
            os.path.getsize(filepath),
            file.filename
        ))

        conn.commit()  
        dataset_id = cursor.lastrowid

        for i, row in df.iterrows():
            row_data = row.to_json()
            cursor.execute("""
                INSERT INTO Data_Row (dataset_id, row_no, row_data)
                VALUES (%s, %s, %s)
            """, (dataset_id, i + 1, row_data))

        conn.commit() 

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        cursor.close()
        conn.close()

    return JSONResponse({
        "message": "CSV uploaded and data stored successfully!",
        "dataset_id": dataset_id,
        "rows_inserted": len(df)
    })

@app.post("/create_experiment")
async def create_experiment(
    experiment_name: str = Body(...),
    description: str = Body(""),
    model_type: str = Body(None),
    hyperparameters: str = Body(None),
    status: str = Body("created"),
    train_dataset_id: int = Body(...),
    test_dataset_id: int = Body(...),
    model_id: int = Body(None), 
    relationship_type: str = Body("trained_with")
):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Experiment (
                experiment_name, description, model_type, hyperparameters, status, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            experiment_name,
            description,
            model_type,
            hyperparameters,
            status,
            datetime.now()
        ))
        conn.commit()
        experiment_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO Experiment_Dataset (experiment_id, data_id, usage_type)
            VALUES (%s, %s, %s)
        """, (experiment_id, train_dataset_id, "train"))
        cursor.execute("""
            INSERT INTO Experiment_Dataset (experiment_id, data_id, usage_type)
            VALUES (%s, %s, %s)
        """, (experiment_id, test_dataset_id, "test"))
        conn.commit()

        if model_id:
            cursor.execute("""
                INSERT INTO Experiment_Model (exp_id, model_id, relationship_type)
                VALUES (%s, %s, %s)
            """, (experiment_id, model_id, relationship_type))
            conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        cursor.close()
        conn.close()

    return JSONResponse({
        "message": "Experiment created successfully!",
        "experiment_id": experiment_id,
        "linked_datasets": {
            "train_dataset_id": train_dataset_id,
            "test_dataset_id": test_dataset_id
        },
        "linked_model": model_id or "No model linked"
    })

@app.get("/get_experiments")
async def get_experiments():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT 
                e.experiment_id,
                e.experiment_name,
                e.model_type,
                e.status,
                e.created_at,
                e.description,
                ed.usage_type,
                d.dataset_name,
                m.model_name,
                em.relationship_type
            FROM Experiment e
            LEFT JOIN Experiment_Dataset ed ON e.experiment_id = ed.experiment_id
            LEFT JOIN Dataset d ON ed.data_id = d.dataset_id
            LEFT JOIN Experiment_Model em ON e.experiment_id = em.exp_id
            LEFT JOIN Model m ON em.model_id = m.model_id
            ORDER BY e.experiment_id;
        """)

        rows = cursor.fetchall()
        experiments = {}

        for row in rows:
            exp_id = row["experiment_id"]
            if exp_id not in experiments:
                experiments[exp_id] = {
                    "experiment_id": exp_id,
                    "experiment_name": row["experiment_name"],
                    "model_type": row["model_type"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "description": row["description"],
                    "datasets": {},
                    "model": None
                }

            if row["usage_type"]:
                experiments[exp_id]["datasets"][row["usage_type"]] = row["dataset_name"]

            if row["model_name"]:
                experiments[exp_id]["model"] = {
                    "model_name": row["model_name"],
                    "relationship_type": row["relationship_type"]
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        cursor.close()
        conn.close()

    return list(experiments.values())

@app.post("/detect_contamination")
async def detect_contamination(
    exper_id: int = Body(...),
    train_dataset_id: int = Body(...),
    test_dataset_id: int = Body(...)
):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT row_no, row_hash FROM Data_Row WHERE dataset_id = %s", (train_dataset_id,))
        train_rows = cursor.fetchall()

        cursor.execute("SELECT row_no, row_hash FROM Data_Row WHERE dataset_id = %s", (test_dataset_id,))
        test_rows = cursor.fetchall()

        if not train_rows or not test_rows:
            raise HTTPException(status_code=404, detail="One or both datasets are empty or missing")

        test_hash_map = {row["row_hash"]: row["row_no"] for row in test_rows if row["row_hash"]}

        contaminated = []
        for train in train_rows:
            if train["row_hash"] in test_hash_map:
                contaminated.append((
                    train["row_hash"],
                    train_dataset_id,
                    test_dataset_id,
                    train["row_no"],
                    test_hash_map[train["row_hash"]],
                ))

        contamination_count = len(contaminated)
        contamination_percentage = (contamination_count / len(test_rows)) * 100 if test_rows else 0.0

        cursor.execute("""
            INSERT INTO Contamination_Report (
                exper_id, contaminated_rows_count, contamination_percentage, status, contamination_details
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            exper_id,
            contamination_count,
            contamination_percentage,
            "completed",
            f"Detected {contamination_count} contaminated rows between datasets {train_dataset_id} and {test_dataset_id}"
        ))
        conn.commit()

        report_id = cursor.lastrowid

        if contaminated:
            cursor.executemany("""
                INSERT INTO Contaminated_Row (
                    report_id, row_hash, train_dataset_id, test_dataset_id, train_row_number, test_row_number
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, [(report_id, *row) for row in contaminated])
            conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Contamination detection failed: {str(e)}")

    finally:
        cursor.close()
        conn.close()

    return JSONResponse({
        "message": "Contamination detection completed",
        "experiment_id": exper_id,
        "report_id": report_id,
        "contaminated_rows": contamination_count,
        "contamination_percentage": contamination_percentage
    })







# from fastapi import FastAPI, HTTPException
# from db import get_connection
# from analysis import calculate_contamination, get_alert_level

# app = FastAPI()

# @app.get("/")
# def home():
#     return {"message": "Contamination Analysis API get is running"}

# @app.get("/experiments")
# def list_experiments():
#     conn = get_connection()
#     cur = conn.cursor(dictionary=True)
#     cur.execute("SELECT * FROM Experiment")
#     data = cur.fetchall()
#     cur.close()
#     conn.close()
#     return {"experiments": data}


# @app.get("/experiments/{experiment_id}/contamination")
# def contamination_report(experiment_id: int):
#     data = calculate_contamination(experiment_id)
#     if not data:
#         raise HTTPException(status_code=404, detail="Experiment not found")
#     level = get_alert_level(data["contamination_percentage"])
#     return {"experiment_id": experiment_id, "contamination": data, "severity": level}


# @app.get("/alerts")
# def get_alerts():
#     conn = get_connection()
#     cur = conn.cursor(dictionary=True)
#     cur.execute("""
#         SELECT e.experiment_name, r.contamination_percentage,
#                CASE
#                     WHEN r.contamination_percentage = 0 THEN 'Clean'
#                     WHEN r.contamination_percentage <= 0.05 THEN 'Low'
#                     WHEN r.contamination_percentage <= 0.15 THEN 'Medium'
#                     ELSE 'High'
#                END AS severity
#         FROM Contamination_Report r
#         JOIN Experiment e ON e.experiment_id = r.exper_id
#         WHERE r.contamination_percentage > 0
#         ORDER BY r.contamination_percentage DESC
#     """)
#     data = cur.fetchall()
#     cur.close()
#     conn.close()
#     return {"alerts": data}
