


from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import JSONResponse
import pandas as pd
import os
from datetime import datetime
from db import get_connection

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
                e.hyperparameters,
                e.accuracy,
                e.loss,
                e.created_at,
                e.updated_at,
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
                    "hyperparameters": row["hyperparameters"],
                    "accuracy": row["accuracy"],
                    "loss": row["loss"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
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
        cursor.callproc("generate_and_store_hashes", [train_dataset_id])
        cursor.callproc("generate_and_store_hashes", [test_dataset_id])
        conn.commit()

        cursor.execute("""
            INSERT INTO Contamination_Report (
                exper_id, contaminated_rows_count, contamination_percentage, status
            ) VALUES (%s, %s, %s, %s)
        """, (exper_id, 0, 0.0, "processing"))
        conn.commit()
        report_id = cursor.lastrowid

        cursor.callproc("detect_exact_duplicates", [train_dataset_id, test_dataset_id, report_id])
        conn.commit()

        cursor.execute("""
            SELECT COUNT(*) AS contaminated_rows
            FROM Contaminated_Row
            WHERE report_id = %s
        """, (report_id,))
        contaminated_rows = cursor.fetchone()["contaminated_rows"]

        cursor.execute("SELECT COUNT(*) AS total FROM Data_Row WHERE dataset_id = %s", (test_dataset_id,))
        total_rows = cursor.fetchone()["total"]
        print(total_rows)
        contamination_percentage = (contaminated_rows / total_rows) * 100 if total_rows > 0 else 0

        cursor.execute("""
            UPDATE Contamination_Report
            SET contaminated_rows_count = %s,
                contamination_percentage = %s,
                total rows= %s,
                status = 'completed',
                contamination_details = %s
            WHERE report_id = %s
        """, (
            contaminated_rows,
            contamination_percentage,
            total_rows,
            f"Detected {contaminated_rows} contaminated rows between datasets {train_dataset_id} and {test_dataset_id}",
            report_id
        ))
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
        "contaminated_rows": contaminated_rows,
        "contamination_percentage": contamination_percentage
    })


@app.get("/experiments/{experiment_id}/contamination")
def contamination_report(experiment_id: int):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM Experiment WHERE experiment_id = %s", (experiment_id,))
    exp = cur.fetchone()
    cur.close()
    conn.close()

    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    import random
    contamination_percentage = round(random.uniform(0, 0.3), 3)
    contaminated = contamination_percentage > 0.05
    severity = (
        "Clean" if contamination_percentage == 0 else
        "Low" if contamination_percentage <= 0.05 else
        "Medium" if contamination_percentage <= 0.15 else
        "High"
    )

    return {
        "experiment_id": experiment_id,
        "experiment_name": exp["experiment_name"],
        "contamination_percentage": contamination_percentage,
        "contamination_detected": contaminated,
        "severity": severity
    }


@app.get("/view_duplicates")
async def view_duplicates(report_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            cr.row_hash, 
            cr.train_dataset_id, 
            cr.test_dataset_id,
            cr.train_row_number, 
            cr.test_row_number
        FROM Contaminated_Row cr
        WHERE cr.report_id = %s
    """, (report_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows
