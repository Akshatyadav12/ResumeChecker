import sqlite3
import json
from datetime import datetime

DB_PATH = "data/resumechecker.db"

def connect():
    return sqlite3.connect(DB_PATH)

def init_db():
    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            score INTEGER NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            score REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()

def save_analysis(filename, score, result):
    connection = connect()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO analyses
        (filename, score, result_json, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            filename,
            int(score),
            json.dumps(result),
            datetime.now().isoformat()
        )
    )

    connection.commit()
    analysis_id = cursor.lastrowid
    connection.close()

    return analysis_id

def save_interview(question, answer, score):
    connection = connect()

    connection.execute(
        """
        INSERT INTO interviews
        (question, answer, score, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            question,
            answer,
            float(score),
            datetime.now().isoformat()
        )
    )

    connection.commit()
    connection.close()

def get_history():
    connection = connect()

    rows = connection.execute(
        """
        SELECT id, filename, score, created_at
        FROM analyses
        ORDER BY id DESC
        LIMIT 20
        """
    ).fetchall()

    connection.close()

    return [
        {
            "id": row[0],
            "filename": row[1],
            "score": row[2],
            "created_at": row[3]
        }
        for row in rows
    ]
