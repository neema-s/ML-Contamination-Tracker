import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="icarusfall$",
        database="ml_experiment_tracker"
    )
