from fastapi import FastAPI, HTTPException
from db import get_connection
from analysis import calculate_contamination, get_alert_level

app = FastAPI()

@app.get("GET /")
def home():
    return {"message": "Contamination Analysis API get is running"}

@app.get("/experiments")
def list_experiments():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM Experiment")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return {"experiments": data}


@app.get("/experiments/{experiment_id}/contamination")
def contamination_report(experiment_id: int):
    data = calculate_contamination(experiment_id)
    if not data:
        raise HTTPException(status_code=404, detail="Experiment not found")
    level = get_alert_level(data["contamination_percentage"])
    return {"experiment_id": experiment_id, "contamination": data, "severity": level}


@app.get("/alerts")
def get_alerts():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT e.experiment_name, r.contamination_percentage,
               CASE
                    WHEN r.contamination_percentage = 0 THEN 'Clean'
                    WHEN r.contamination_percentage <= 0.05 THEN 'Low'
                    WHEN r.contamination_percentage <= 0.15 THEN 'Medium'
                    ELSE 'High'
               END AS severity
        FROM Contamination_Report r
        JOIN Experiment e ON e.experiment_id = r.exper_id
        WHERE r.contamination_percentage > 0
        ORDER BY r.contamination_percentage DESC
    """)
    data = cur.fetchall()
    cur.close()
    conn.close()
    return {"alerts": data}
