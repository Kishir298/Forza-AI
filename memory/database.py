import sqlite3
import os


DATABASE = "data/forza_memory.db"


def get_connection():
    os.makedirs("data", exist_ok=True)

    return sqlite3.connect(DATABASE)


def create_tables():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        information TEXT,
        importance INTEGER
    )
    """)

    connection.commit()
    connection.close()
