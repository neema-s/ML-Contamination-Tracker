from db import get_connection

def calculate_contamination(experiment_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT contaminated_rows_count, contamination_percentage
        FROM Contamination_Report
        WHERE exper_id = %s
        ORDER BY generated_at DESC
        LIMIT 1
    """, (experiment_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()
    return result if result else {"contamination_percentage": 0, "contaminated_rows_count": 0}

def get_alert_level(percentage):
    if percentage == 0:
        return "Clean"
    elif percentage <= 0.05:
        return "Low"
    elif percentage <= 0.15:
        return "Medium"
    else:
        return "High"
