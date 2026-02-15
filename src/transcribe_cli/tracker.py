import sqlite3
from pathlib import Path

from .config import TRACKER_DIR, TRACKER_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    input_path TEXT UNIQUE NOT NULL,
    output_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    duration_seconds REAL,
    processing_seconds REAL,
    model TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);
"""


class Tracker:
    def __init__(self, output_dir: Path):
        db_dir = output_dir / TRACKER_DIR
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_dir / TRACKER_DB
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def add_file(self, input_path: str, output_path: str, model: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO files (input_path, output_path, model) VALUES (?, ?, ?)",
            (input_path, output_path, model),
        )
        self.conn.commit()

    def get_status(self, input_path: str) -> str | None:
        row = self.conn.execute(
            "SELECT status FROM files WHERE input_path = ?", (input_path,)
        ).fetchone()
        return row["status"] if row else None

    def mark_processing(self, input_path: str) -> None:
        self.conn.execute(
            "UPDATE files SET status = 'processing' WHERE input_path = ?",
            (input_path,),
        )
        self.conn.commit()

    def mark_completed(
        self,
        input_path: str,
        duration_seconds: float | None = None,
        processing_seconds: float | None = None,
    ) -> None:
        self.conn.execute(
            """UPDATE files SET status = 'completed', completed_at = datetime('now'),
               duration_seconds = ?, processing_seconds = ?
               WHERE input_path = ?""",
            (duration_seconds, processing_seconds, input_path),
        )
        self.conn.commit()

    def mark_failed(self, input_path: str, error: str) -> None:
        self.conn.execute(
            "UPDATE files SET status = 'failed', error = ? WHERE input_path = ?",
            (error, input_path),
        )
        self.conn.commit()

    def get_pending_files(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM files WHERE status = 'pending'"
        ).fetchall()

    def get_failed_files(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM files WHERE status = 'failed'"
        ).fetchall()

    def reset_failed(self) -> int:
        cursor = self.conn.execute(
            "UPDATE files SET status = 'pending', error = NULL WHERE status = 'failed'"
        )
        self.conn.commit()
        return cursor.rowcount

    def get_summary(self) -> dict:
        rows = self.conn.execute(
            """SELECT status, COUNT(*) as count,
                      SUM(duration_seconds) as total_duration,
                      SUM(processing_seconds) as total_processing
               FROM files GROUP BY status"""
        ).fetchall()
        summary = {
            "total": 0,
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "total_duration": 0.0,
            "total_processing": 0.0,
        }
        for row in rows:
            summary[row["status"]] = row["count"]
            summary["total"] += row["count"]
            if row["total_duration"]:
                summary["total_duration"] += row["total_duration"]
            if row["total_processing"]:
                summary["total_processing"] += row["total_processing"]
        return summary

    def get_all_files(
        self, status: str | None = None, sort: str = "name"
    ) -> list[sqlite3.Row]:
        query = "SELECT * FROM files"
        params: list[str] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        sort_col = {
            "name": "input_path",
            "status": "status",
            "duration": "duration_seconds",
        }.get(sort, "input_path")
        query += f" ORDER BY {sort_col}"
        return self.conn.execute(query, params).fetchall()

    def close(self) -> None:
        self.conn.close()
