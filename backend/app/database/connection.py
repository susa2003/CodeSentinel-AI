import sqlite3
from pathlib import Path
from contextlib import contextmanager
from backend.app.config import settings

def init_db():
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.DATABASE_PATH))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    cursor = conn.cursor()

    # Sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        tool_calls_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
    )
    """)

    # Datasets
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS datasets (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        stored_path TEXT NOT NULL,
        row_count INTEGER NOT NULL,
        column_count INTEGER NOT NULL,
        has_timestamps INTEGER NOT NULL DEFAULT 0,
        metadata_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # Analysis records
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis_records (
        id TEXT PRIMARY KEY,
        record_type TEXT NOT NULL,
        title TEXT NOT NULL,
        input_summary_json TEXT NOT NULL,
        result_json TEXT NOT NULL,
        dataset_id TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Reports
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        stored_path TEXT NOT NULL,
        report_type TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        title TEXT NOT NULL,
        findings_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(str(settings.DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
