import json
import os
import sqlite3


DATABASE = "data/forza_memory.db"


def get_connection():
    """Return a connection to Forza's SQLite database."""

    os.makedirs("data", exist_ok=True)

    return sqlite3.connect(DATABASE)


def create_tables():
    """Create all memory-related database tables."""

    connection = get_connection()
    cursor = connection.cursor()

    # General Forza memories
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        information TEXT,
        importance INTEGER
    )
    """)

    # Historical data produced by monitoring collectors
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS collector_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        component TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        data TEXT NOT NULL
    )
    """)

    connection.commit()
    connection.close()


def save_memory(category, information, importance=1):
    """Save a general memory."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO memories (
            category,
            information,
            importance
        )
        VALUES (?, ?, ?)
        """,
        (
            category,
            information,
            importance,
        ),
    )

    connection.commit()
    connection.close()


def save_collector_data(data):
    """Save processed collector data."""

    if not isinstance(data, dict):
        raise TypeError("Collector data must be a dictionary.")

    component = data.get("component")

    if not component:
        raise ValueError(
            "Collector data must contain a 'component' field."
        )

    timestamp = data.get("timestamp")

    if not timestamp:
        raise ValueError(
            "Collector data must contain a 'timestamp' field."
        )

    serialized_data = json.dumps(
        data,
        ensure_ascii=False,
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO collector_data (
            component,
            timestamp,
            data
        )
        VALUES (?, ?, ?)
        """,
        (
            component,
            timestamp,
            serialized_data,
        ),
    )

    connection.commit()
    connection.close()


def get_collector_history(component, limit=100):
    """Return recent historical data for a collector."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT data
        FROM collector_data
        WHERE component = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            component,
            limit,
        ),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        json.loads(row[0])
        for row in rows
    ]


create_tables()