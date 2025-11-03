from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
import pandas as pd
import os
from db import get_connection
from datetime import datetime

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
    cursor = conn.cursor()

    try:
        # Insert dataset using stored procedure
        cursor.callproc(
            "insert_dataset",
            (
                file.filename,
                filepath,
                file.filename,
                "csv",
                "uploaded",
                "User uploaded dataset",
                os.path.getsize(filepath),
                file.filename,  # checksum seed
            ),
        )

        # Retrieve dataset_id from stored procedure result
        dataset_id = None
        for result in cursor.stored_results():
            res = result.fetchone()
            if res and len(res) > 0:
                dataset_id = res[0]

        if not dataset_id:
            raise HTTPException(status_code=500, detail="Failed to retrieve dataset_id.")

        # Insert rows
        for i, row in df.iterrows():
            cursor.callproc("insert_data_row", (dataset_id, row.to_json(), i + 1))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        cursor.close()
        conn.close()

    return JSONResponse(
        {
            "message": "CSV uploaded and data stored successfully!",
            "dataset_id": dataset_id,
            "rows_inserted": len(df),
        }
    )

@app.get("/datasets")
def get_all_datasets():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.callproc("get_all_datasets")
    data = []
    for result in cursor.stored_results():
        data.extend(result.fetchall())
    cursor.close()
    conn.close()
    return data


@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.callproc("get_dataset", (dataset_id,))
    result = next(cursor.stored_results()).fetchone()
    cursor.close()
    conn.close()
    if not result:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return result


@app.put("/datasets/{dataset_id}")
def update_dataset(dataset_id: int, name: str = Form(...), description: str = Form(""), version: str = Form("v1")):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.callproc("update_dataset", (dataset_id, name, description, version))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Dataset {dataset_id} updated successfully."}


@app.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.callproc("delete_dataset", (dataset_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Dataset {dataset_id} deleted successfully."}


@app.get("/datasets/{dataset_id}/stats")
def dataset_stats(dataset_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.callproc("get_dataset_stats", (dataset_id,))
    result = next(cursor.stored_results()).fetchone()
    cursor.close()
    conn.close()
    return result


@app.get("/datasets/{dataset_id}/rows")
def get_dataset_rows(dataset_id: int, limit: int = 10, offset: int = 0):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.callproc("get_dataset_rows", (dataset_id, limit, offset))
    rows = next(cursor.stored_results()).fetchall()
    cursor.close()
    conn.close()
    return rows


@app.post("/datasets/{dataset_id}/generate_hashes")
def generate_hashes(dataset_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.callproc("generate_and_store_hashes", (dataset_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Hashes generated for dataset {dataset_id}"}


@app.post("/experiments/create")
def create_experiment(
    experiment_name: str = Form(...),
    model_type: str = Form(...),
    hyperparameters: str = Form(""),
    description: str = Form(""),
    dataset_id: int = Form(None),
    test_dataset_id: int = Form(None),
    model_id: int = Form(None),
):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO Experiment (experiment_name, model_type, hyperparameters, description, status)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (experiment_name, model_type, hyperparameters, description, "created"),
        )
        conn.commit()
        experiment_id = cursor.lastrowid

        # Link train dataset
        if dataset_id:
            cursor.execute(
                """
                INSERT INTO Experiment_Dataset (experiment_id, data_id, usage_type)
                VALUES (%s, %s, %s)
            """,
                (experiment_id, dataset_id, "train"),
            )

        # Link test dataset
        if test_dataset_id:
            cursor.execute(
                """
                INSERT INTO Experiment_Dataset (experiment_id, data_id, usage_type)
                VALUES (%s, %s, %s)
            """,
                (experiment_id, test_dataset_id, "test"),
            )

        # Link model
        if model_id:
            cursor.execute(
                """
                INSERT INTO Experiment_Model (exp_id, model_id, relationship_type)
                VALUES (%s, %s, %s)
            """,
                (experiment_id, model_id, "primary"),
            )

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

    return {"message": "Experiment created successfully!", "experiment_id": experiment_id}


@app.get("/experiments")
def get_all_experiments():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Experiment")
    experiments = cursor.fetchall()
    cursor.close()
    conn.close()
    return experiments


@app.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Experiment WHERE experiment_id = %s", (experiment_id,))
    exp = cursor.fetchone()
    cursor.close()
    conn.close()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@app.post("/detect_contamination")
def detect_contamination(train_dataset_id: int = Form(...), test_dataset_id: int = Form(...), report_id: int = Form(...)):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.callproc("detect_exact_duplicates", (train_dataset_id, test_dataset_id, report_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    return {"message": f"Contamination detection complete for report {report_id}"}


@app.get("/reports")
def get_all_reports():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Contamination_Report ORDER BY generated_at DESC")
    reports = cursor.fetchall()
    cursor.close()
    conn.close()
    return reports


@app.get("/reports/{report_id}")
def get_report(report_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Contamination_Report WHERE report_id = %s", (report_id,))
    report = cursor.fetchone()
    cursor.close()
    conn.close()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ---------- Additional APIs to call procedures/functions/views and exercise triggers ----------

@app.get("/health/datasets")
def get_dataset_health_check():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM dataset_health_check ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.get("/experiments/{experiment_id}/contamination/summary")
def get_experiment_contamination_summary(experiment_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT 
                calculate_contamination_percentage(%s) AS contamination_percentage,
                contamination_severity_level(calculate_contamination_percentage(%s)) AS severity
            """,
            (experiment_id, experiment_id),
        )
        result = cursor.fetchone() or {"contamination_percentage": 0.0, "severity": "Clean"}
        return {"experiment_id": experiment_id, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.post("/reports/generate")
def generate_report(experiment_id: int = Form(...)):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.callproc("generate_contamination_report", (experiment_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
    return {"message": f"Report generated for experiment {experiment_id}"}


@app.get("/experiments/{experiment_id}/patterns")
def analyze_patterns(experiment_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.callproc("analyze_contamination_patterns", (experiment_id,))
        data = []
        for result in cursor.stored_results():
            data.extend(result.fetchall())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.post("/reports/flag_high_risk")
def flag_high_risk(risk_threshold: float = Form(...)):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.callproc("flag_high_risk_experiments", (risk_threshold,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
    return {"message": f"Flagged experiments above {risk_threshold}% contamination"}


@app.put("/experiments/{experiment_id}")
def update_experiment(
    experiment_id: int,
    experiment_name: str = Form(None),
    description: str = Form(None),
    model_type: str = Form(None),
    hyperparameters: str = Form(None),
    accuracy: float = Form(None),
    loss: float = Form(None),
    status: str = Form(None),
):
    # This update will trigger any BEFORE/AFTER UPDATE triggers on Experiment (e.g., timestamp)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        update_fields = []
        values = []

        if experiment_name is not None:
            update_fields.append("experiment_name = %s")
            values.append(experiment_name)
        if description is not None:
            update_fields.append("description = %s")
            values.append(description)
        if model_type is not None:
            update_fields.append("model_type = %s")
            values.append(model_type)
        if hyperparameters is not None:
            update_fields.append("hyperparameters = %s")
            values.append(hyperparameters)
        if accuracy is not None:
            update_fields.append("accuracy = %s")
            values.append(accuracy)
        if loss is not None:
            update_fields.append("loss = %s")
            values.append(loss)
        if status is not None:
            update_fields.append("status = %s")
            values.append(status)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        query = f"UPDATE Experiment SET {', '.join(update_fields)} WHERE experiment_id = %s"
        values.append(experiment_id)
        cursor.execute(query, tuple(values))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {"message": "Experiment updated"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.get("/views/experiment_risk_scores")
def get_experiment_risk_scores():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM experiment_risk_scores ORDER BY generated_at DESC")
        return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()






# from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Form
# from fastapi.responses import JSONResponse
# import pandas as pd
# import os
# from datetime import datetime
# from db_config import get_connection
# import hashlib
# import shutil

# app = FastAPI(title="ML Experiment Tracker API")

# MODEL_FOLDER = "models"
# os.makedirs(MODEL_FOLDER, exist_ok=True)

# UPLOAD_FOLDER = "uploads"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# @app.post("/upload")
# async def upload_csv(file: UploadFile = File(...)):

#     if not file.filename.endswith(".csv"):
#         raise HTTPException(status_code=400, detail="Only CSV files are allowed")

#     filepath = os.path.join(UPLOAD_FOLDER, file.filename)

#     with open(filepath, "wb") as f:
#         f.write(await file.read())

#     try:
#         df = pd.read_csv(filepath)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")

#     conn = get_connection()

#     cursor = conn.cursor(buffered=True)

#     try:
#         cursor.execute("""
#             INSERT INTO Dataset (
#                 dataset_name, filepath, filename, file_format,
#                 dataset_type, description, filesize, checksum
#             )
#             VALUES (%s, %s, %s, %s, %s, %s, %s, SHA2(%s, 256))
#         """, (
#             file.filename,
#             filepath,
#             file.filename,
#             "csv",
#             "uploaded",
#             "User uploaded dataset",
#             os.path.getsize(filepath),
#             file.filename
#         ))

#         conn.commit()  
#         dataset_id = cursor.lastrowid

#         for i, row in df.iterrows():
#             row_data = row.to_json()
#             row_hash = hashlib.sha256(row_data.encode()).hexdigest()
#             cursor.execute("""
#                 INSERT INTO Data_Row (dataset_id, row_no, row_data, row_hash)
#                 VALUES (%s, %s, %s, %s)
#             """, (dataset_id, i + 1, row_data, row_hash))

#         conn.commit() 

#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

#     finally:
#         cursor.close()
#         conn.close()

#     return JSONResponse({
#         "message": "CSV uploaded and data stored successfully!",
#         "dataset_id": dataset_id,
#         "rows_inserted": len(df)
#     })

# @app.post("/create_experiment")
# async def create_experiment(
#     experiment_name: str = Body(...),
#     description: str = Body(""),
#     model_type: str = Body(None),
#     hyperparameters: str = Body(None),
#     status: str = Body("created"),
#     train_dataset_id: int = Body(...),
#     test_dataset_id: int = Body(...),
#     model_id: int = Body(None), 
#     relationship_type: str = Body("trained_with")
# ):
#     conn = get_connection()
#     cursor = conn.cursor()

#     try:
#         cursor.execute("""
#             INSERT INTO Experiment (
#                 experiment_name, description, model_type, hyperparameters, status, created_at
#             )
#             VALUES (%s, %s, %s, %s, %s, %s)
#         """, (
#             experiment_name,
#             description,
#             model_type,
#             hyperparameters,
#             status,
#             datetime.now()
#         ))
#         conn.commit()
#         experiment_id = cursor.lastrowid

#         cursor.execute("""
#             INSERT INTO Experiment_Dataset (experiment_id, data_id, usage_type)
#             VALUES (%s, %s, %s)
#         """, (experiment_id, train_dataset_id, "train"))
#         cursor.execute("""
#             INSERT INTO Experiment_Dataset (experiment_id, data_id, usage_type)
#             VALUES (%s, %s, %s)
#         """, (experiment_id, test_dataset_id, "test"))
#         conn.commit()

#         if model_id:
#             cursor.execute("""
#                 INSERT INTO Experiment_Model (exp_id, model_id, relationship_type)
#                 VALUES (%s, %s, %s)
#             """, (experiment_id, model_id, relationship_type))
#             conn.commit()

#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

#     finally:
#         cursor.close()
#         conn.close()

#     return JSONResponse({
#         "message": "Experiment created successfully!",
#         "experiment_id": experiment_id,
#         "linked_datasets": {
#             "train_dataset_id": train_dataset_id,
#             "test_dataset_id": test_dataset_id
#         },
#         "linked_model": model_id or "No model linked"
#     })

# @app.get("/get_experiments")
# async def get_experiments():
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)

#     try:
#         cursor.execute("""
#             SELECT 
#                 e.experiment_id,
#                 e.experiment_name,
#                 e.model_type,
#                 e.status,
#                 e.created_at,
#                 e.description,
#                 ed.usage_type,
#                 d.dataset_name,
#                 m.model_name,
#                 em.relationship_type
#             FROM Experiment e
#             LEFT JOIN Experiment_Dataset ed ON e.experiment_id = ed.experiment_id
#             LEFT JOIN Dataset d ON ed.data_id = d.dataset_id
#             LEFT JOIN Experiment_Model em ON e.experiment_id = em.exp_id
#             LEFT JOIN Model m ON em.model_id = m.model_id
#             ORDER BY e.experiment_id;
#         """)

#         rows = cursor.fetchall()
#         experiments = {}

#         for row in rows:
#             exp_id = row["experiment_id"]
#             if exp_id not in experiments:
#                 experiments[exp_id] = {
#                     "experiment_id": exp_id,
#                     "experiment_name": row["experiment_name"],
#                     "model_type": row["model_type"],
#                     "status": row["status"],
#                     "created_at": row["created_at"],
#                     "description": row["description"],
#                     "datasets": {},
#                     "model": None
#                 }

#             if row["usage_type"]:
#                 experiments[exp_id]["datasets"][row["usage_type"]] = row["dataset_name"]

#             if row["model_name"]:
#                 experiments[exp_id]["model"] = {
#                     "model_name": row["model_name"],
#                     "relationship_type": row["relationship_type"]
#                 }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

#     finally:
#         cursor.close()
#         conn.close()

#     return list(experiments.values())

# @app.get("/get_experiment/{experiment_id}")
# async def get_experiment(experiment_id: int = Path(..., description="Experiment ID")):
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)

#     try:
#         cursor.execute("""
#             SELECT 
#                 e.experiment_id,
#                 e.experiment_name,
#                 e.model_type,
#                 e.status,
#                 e.created_at,
#                 e.description,
#                 e.hyperparameters,
#                 e.accuracy,
#                 e.loss,
#                 ed.usage_type,
#                 d.dataset_id,
#                 d.dataset_name,
#                 m.model_id,
#                 m.model_name,
#                 em.relationship_type
#             FROM Experiment e
#             LEFT JOIN Experiment_Dataset ed ON e.experiment_id = ed.experiment_id
#             LEFT JOIN Dataset d ON ed.data_id = d.dataset_id
#             LEFT JOIN Experiment_Model em ON e.experiment_id = em.exp_id
#             LEFT JOIN Model m ON em.model_id = m.model_id
#             WHERE e.experiment_id = %s;
#         """, (experiment_id,))

#         rows = cursor.fetchall()
#         if not rows:
#             raise HTTPException(status_code=404, detail="Experiment not found")

#         exp = rows[0]
#         result = {
#             "experiment_id": exp["experiment_id"],
#             "experiment_name": exp["experiment_name"],
#             "model_type": exp["model_type"],
#             "status": exp["status"],
#             "created_at": exp["created_at"],
#             "description": exp["description"],
#             "hyperparameters": exp["hyperparameters"],
#             "accuracy": exp["accuracy"],
#             "loss": exp["loss"],
#             "datasets": {},
#             "model": None
#         }

#         for row in rows:
#             if row["usage_type"]:
#                 result["datasets"][row["usage_type"]] = {
#                     "dataset_id": row["dataset_id"],
#                     "dataset_name": row["dataset_name"]
#                 }
#             if row["model_name"]:
#                 result["model"] = {
#                     "model_id": row["model_id"],
#                     "model_name": row["model_name"],
#                     "relationship_type": row["relationship_type"]
#                 }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

#     finally:
#         cursor.close()
#         conn.close()

#     return JSONResponse(result)

# @app.put("/update_experiment/{experiment_id}")
# async def update_experiment(
#     experiment_id: int = Path(..., description="Experiment ID to update"),
#     experiment_name: str = Body(None),
#     description: str = Body(None),
#     model_type: str = Body(None),
#     hyperparameters: str = Body(None),
#     accuracy: float = Body(None),
#     loss: float = Body(None),
#     status: str = Body(None)
# ):
#     conn = get_connection()
#     cursor = conn.cursor()

#     try:
#         update_fields = []
#         values = []

#         if experiment_name:
#             update_fields.append("experiment_name = %s")
#             values.append(experiment_name)
#         if description:
#             update_fields.append("description = %s")
#             values.append(description)
#         if model_type:
#             update_fields.append("model_type = %s")
#             values.append(model_type)
#         if hyperparameters:
#             update_fields.append("hyperparameters = %s")
#             values.append(hyperparameters)
#         if accuracy is not None:
#             update_fields.append("accuracy = %s")
#             values.append(accuracy)
#         if loss is not None:
#             update_fields.append("loss = %s")
#             values.append(loss)
#         if status:
#             update_fields.append("status = %s")
#             values.append(status)

#         if not update_fields:
#             raise HTTPException(status_code=400, detail="No fields provided for update")

#         query = f"""
#             UPDATE Experiment
#             SET {', '.join(update_fields)}, updated_at = NOW()
#             WHERE experiment_id = %s
#         """
#         values.append(experiment_id)
#         cursor.execute(query, tuple(values))
#         conn.commit()

#         if cursor.rowcount == 0:
#             raise HTTPException(status_code=404, detail="Experiment not found")

#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

#     finally:
#         cursor.close()
#         conn.close()

#     return JSONResponse({"message": "Experiment updated successfully", "experiment_id": experiment_id})

# @app.post("/upload_model")
# async def upload_model(
#     model_name: str = Form(...),
#     framework: str = Form("unknown"),
#     description: str = Form(""),
#     model_file: UploadFile = File(...)
# ):
#     allowed_exts = (".pkl", ".joblib", ".h5", ".pt", ".sav")
#     if not any(model_file.filename.endswith(ext) for ext in allowed_exts):
#         raise HTTPException(status_code=400, detail=f"Allowed file types: {allowed_exts}")

#     model_path = os.path.join(MODEL_FOLDER, model_file.filename)
#     with open(model_path, "wb") as buffer:
#         shutil.copyfileobj(model_file.file, buffer)

#     conn = get_connection()
#     cursor = conn.cursor()

#     try:
#         cursor.execute("""
#             INSERT INTO Model (model_name, model_path, framework, description, model_size)
#             VALUES (%s, %s, %s, %s, %s)
#         """, (
#             model_name,
#             model_path,
#             framework,
#             description,
#             os.path.getsize(model_path) / (1024 * 1024)
#         ))
#         conn.commit()
#         model_id = cursor.lastrowid
#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
#     finally:
#         cursor.close()
#         conn.close()

#     return JSONResponse({
#         "message": "Model uploaded successfully",
#         "model_id": model_id,
#         "model_name": model_name,
#         "framework": framework
#     })

# @app.get("/get_models")
# async def get_models():
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         cursor.execute("SELECT * FROM Model ORDER BY created_at DESC;")
#         models = cursor.fetchall()
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
#     finally:
#         cursor.close()
#         conn.close()
#     return models

# @app.post("/detect_contamination")
# async def detect_contamination(
#     exper_id: int = Body(...),
#     train_dataset_id: int = Body(...),
#     test_dataset_id: int = Body(...)
# ):
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)

#     try:
#         cursor.execute("SELECT row_no, row_hash FROM Data_Row WHERE dataset_id = %s", (train_dataset_id,))
#         train_rows = cursor.fetchall()

#         cursor.execute("SELECT row_no, row_hash FROM Data_Row WHERE dataset_id = %s", (test_dataset_id,))
#         test_rows = cursor.fetchall()

#         if not train_rows or not test_rows:
#             raise HTTPException(status_code=404, detail="One or both datasets are empty or missing")

#         test_hash_map = {row["row_hash"]: row["row_no"] for row in test_rows if row["row_hash"]}

#         contaminated = []
#         for train in train_rows:
#             if train["row_hash"] in test_hash_map:
#                 contaminated.append((
#                     train["row_hash"],
#                     train_dataset_id,
#                     test_dataset_id,
#                     train["row_no"],
#                     test_hash_map[train["row_hash"]],
#                 ))

#         contamination_count = len(contaminated)
#         contamination_percentage = (contamination_count / len(test_rows)) * 100 if test_rows else 0.0

#         cursor.execute("""
#             INSERT INTO Contamination_Report (
#                 exper_id, contaminated_rows_count, contamination_percentage, status, contamination_details
#             )
#             VALUES (%s, %s, %s, %s, %s)
#         """, (
#             exper_id,
#             contamination_count,
#             contamination_percentage,
#             "completed",
#             f"Detected {contamination_count} contaminated rows between datasets {train_dataset_id} and {test_dataset_id}"
#         ))
#         conn.commit()

#         report_id = cursor.lastrowid

#         if contaminated:
#             cursor.executemany("""
#                 INSERT INTO Contaminated_Row (
#                     report_id, row_hash, train_dataset_id, test_dataset_id, train_row_number, test_row_number
#                 ) VALUES (%s, %s, %s, %s, %s, %s)
#             """, [(report_id, *row) for row in contaminated])
#             conn.commit()

#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Contamination detection failed: {str(e)}")

#     finally:
#         cursor.close()
#         conn.close()

#     return JSONResponse({
#         "message": "Contamination detection completed",
#         "experiment_id": exper_id,
#         "report_id": report_id,
#         "contaminated_rows": contamination_count,
#         "contamination_percentage": contamination_percentage
#     })

# @app.get("/get_reports")
# async def get_reports():
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)

#     try:
#         cursor.execute("""
#             SELECT 
#                 r.report_id,
#                 r.exper_id,
#                 e.experiment_name,
#                 r.generated_at,
#                 r.contaminated_rows_count,
#                 r.contamination_percentage,
#                 r.status,
#                 r.contamination_details
#             FROM Contamination_Report r
#             LEFT JOIN Experiment e ON r.exper_id = e.experiment_id
#             ORDER BY r.generated_at DESC;
#         """)
#         reports = cursor.fetchall()
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
#     finally:
#         cursor.close()
#         conn.close()

#     return reports







# # from fastapi import FastAPI, HTTPException
# # from db import get_connection
# # from analysis import calculate_contamination, get_alert_level

# # app = FastAPI()

# # @app.get("/")
# # def home():
# #     return {"message": "Contamination Analysis API get is running"}

# # @app.get("/experiments")
# # def list_experiments():
# #     conn = get_connection()
# #     cur = conn.cursor(dictionary=True)
# #     cur.execute("SELECT * FROM Experiment")
# #     data = cur.fetchall()
# #     cur.close()
# #     conn.close()
# #     return {"experiments": data}


# # @app.get("/experiments/{experiment_id}/contamination")
# # def contamination_report(experiment_id: int):
# #     data = calculate_contamination(experiment_id)
# #     if not data:
# #         raise HTTPException(status_code=404, detail="Experiment not found")
# #     level = get_alert_level(data["contamination_percentage"])
# #     return {"experiment_id": experiment_id, "contamination": data, "severity": level}


# # @app.get("/alerts")
# # def get_alerts():
# #     conn = get_connection()
# #     cur = conn.cursor(dictionary=True)
# #     cur.execute("""
# #         SELECT e.experiment_name, r.contamination_percentage,
# #                CASE
# #                     WHEN r.contamination_percentage = 0 THEN 'Clean'
# #                     WHEN r.contamination_percentage <= 0.05 THEN 'Low'
# #                     WHEN r.contamination_percentage <= 0.15 THEN 'Medium'
# #                     ELSE 'High'
# #                END AS severity
# #         FROM Contamination_Report r
# #         JOIN Experiment e ON e.experiment_id = r.exper_id
# #         WHERE r.contamination_percentage > 0
# #         ORDER BY r.contamination_percentage DESC
# #     """)
# #     data = cur.fetchall()
# #     cur.close()
# #     conn.close()
# #     return {"alerts": data}
