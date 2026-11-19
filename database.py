"""
database.py
-----------
SQLite persistence layer for the BMI Health Tracker.

Creates "bmi_tracker.db" next to this file and provides Insert, Read,
Update and Delete operations plus search, summaries and CSV export.
All sqlite3 errors are wrapped in DatabaseError so the GUI can show
friendly messages.
"""

import csv
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bmi_tracker.db")
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
CATEGORIES = ["Underweight", "Normal", "Overweight", "Obese"]

CSV_HEADERS = ["Record ID", "Username", "Weight (kg)", "Height (m)",
               "BMI", "BMI Category", "Date and Time"]


class DatabaseError(Exception):
    """Raised for any database connection, read or write problem."""


def _like(keyword):
    """Escape LIKE wildcards and wrap the keyword for substring search."""
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class Database:
    """Thin wrapper around the bmi_records table."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._create_table()

    # ------------------------------------------------------------------ #
    # Connection handling
    # ------------------------------------------------------------------ #
    @contextmanager
    def _connection(self):
        """Open a connection, commit on success, roll back on error, always close."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.row_factory = sqlite3.Row
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not connect to the database: {exc}") from exc
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise DatabaseError(f"Database operation failed: {exc}") from exc
        finally:
            conn.close()

    def _create_table(self):
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bmi_records (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    username    TEXT NOT NULL,
                    weight      REAL NOT NULL,
                    height      REAL NOT NULL,
                    bmi         REAL NOT NULL,
                    category    TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_records_username "
                "ON bmi_records (username COLLATE NOCASE)"
            )

    def _fetch(self, query, params=()):
        with self._connection() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    # ------------------------------------------------------------------ #
    # CREATE
    # ------------------------------------------------------------------ #
    def insert_record(self, username, weight, height, bmi, category, recorded_at=None):
        """Insert a record and return its new ID. Reuses existing username spelling."""
        recorded_at = recorded_at or datetime.now().strftime(DATE_FORMAT)
        with self._connection() as conn:
            existing = conn.execute(
                "SELECT username FROM bmi_records WHERE username = ? COLLATE NOCASE LIMIT 1",
                (username,),
            ).fetchone()
            if existing:
                username = existing["username"]
            cur = conn.execute(
                "INSERT INTO bmi_records (username, weight, height, bmi, category, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (username, weight, height, bmi, category, recorded_at),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------ #
    # READ
    # ------------------------------------------------------------------ #
    def get_record(self, record_id):
        rows = self._fetch("SELECT * FROM bmi_records WHERE id = ?", (record_id,))
        return rows[0] if rows else None

    def get_all_records(self, limit=None):
        """All records, newest first."""
        query = "SELECT * FROM bmi_records ORDER BY recorded_at DESC, id DESC"
        if limit:
            return self._fetch(query + " LIMIT ?", (int(limit),))
        return self._fetch(query)

    def get_records_by_user(self, username):
        """One user's history, oldest first (ready for plotting)."""
        return self._fetch(
            "SELECT * FROM bmi_records WHERE username = ? COLLATE NOCASE "
            "ORDER BY recorded_at ASC, id ASC",
            (username,),
        )

    def search_records(self, keyword="", category=None, exact=False):
        """Search by username (substring or exact) and optional category, newest first."""
        clauses, params = [], []
        keyword = (keyword or "").strip()
        if keyword:
            if exact:
                clauses.append("username = ? COLLATE NOCASE")
                params.append(keyword)
            else:
                clauses.append("username LIKE ? ESCAPE '\\'")
                params.append(_like(keyword))
        if category and category in CATEGORIES:
            clauses.append("category = ?")
            params.append(category)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return self._fetch(
            f"SELECT * FROM bmi_records {where} ORDER BY recorded_at DESC, id DESC",
            tuple(params),
        )

    def get_latest_record(self, username=None):
        if username:
            rows = self._fetch(
                "SELECT * FROM bmi_records WHERE username = ? COLLATE NOCASE "
                "ORDER BY recorded_at DESC, id DESC LIMIT 1",
                (username,),
            )
        else:
            rows = self._fetch(
                "SELECT * FROM bmi_records ORDER BY recorded_at DESC, id DESC LIMIT 1"
            )
        return rows[0] if rows else None

    def get_usernames(self):
        rows = self._fetch(
            "SELECT MIN(username) AS username FROM bmi_records "
            "GROUP BY username COLLATE NOCASE ORDER BY username COLLATE NOCASE"
        )
        return [row["username"] for row in rows]

    def get_user_summaries(self, keyword=""):
        """One row per user: record count, latest BMI/category, average, last update."""
        return self._fetch(
            """
            SELECT MIN(r.username) AS username,
                   COUNT(*)        AS total_records,
                   ROUND(AVG(r.bmi), 2) AS avg_bmi,
                   MAX(r.recorded_at)   AS last_updated,
                   (SELECT bmi FROM bmi_records
                     WHERE username = r.username COLLATE NOCASE
                     ORDER BY recorded_at DESC, id DESC LIMIT 1) AS latest_bmi,
                   (SELECT category FROM bmi_records
                     WHERE username = r.username COLLATE NOCASE
                     ORDER BY recorded_at DESC, id DESC LIMIT 1) AS latest_category
            FROM bmi_records r
            WHERE r.username LIKE ? ESCAPE '\\'
            GROUP BY r.username COLLATE NOCASE
            ORDER BY r.username COLLATE NOCASE
            """,
            (_like((keyword or "").strip()),),
        )

    # ------------------------------------------------------------------ #
    # Counters and statistics
    # ------------------------------------------------------------------ #
    def count_records(self):
        return self._fetch("SELECT COUNT(*) AS n FROM bmi_records")[0]["n"]

    def count_users(self):
        return self._fetch(
            "SELECT COUNT(*) AS n FROM "
            "(SELECT 1 FROM bmi_records GROUP BY username COLLATE NOCASE)"
        )[0]["n"]

    def get_average_bmi(self):
        value = self._fetch("SELECT AVG(bmi) AS a FROM bmi_records")[0]["a"]
        return round(value, 2) if value is not None else None

    def get_category_counts(self):
        counts = {name: 0 for name in CATEGORIES}
        for row in self._fetch(
            "SELECT category, COUNT(*) AS n FROM bmi_records GROUP BY category"
        ):
            if row["category"] in counts:
                counts[row["category"]] = row["n"]
        return counts

    # ------------------------------------------------------------------ #
    # UPDATE
    # ------------------------------------------------------------------ #
    def update_record(self, record_id, weight, height, bmi, category):
        """Update measurements of a record. Returns True if a row changed."""
        with self._connection() as conn:
            cur = conn.execute(
                "UPDATE bmi_records SET weight = ?, height = ?, bmi = ?, category = ? "
                "WHERE id = ?",
                (weight, height, bmi, category, record_id),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    # DELETE
    # ------------------------------------------------------------------ #
    def delete_record(self, record_id):
        return self.delete_records([record_id]) > 0

    def delete_records(self, record_ids):
        """Delete several records by ID. Returns the number removed."""
        ids = [int(i) for i in record_ids]
        if not ids:
            return 0
        with self._connection() as conn:
            cur = conn.executemany("DELETE FROM bmi_records WHERE id = ?", [(i,) for i in ids])
            return cur.rowcount

    def delete_user(self, username):
        """Delete every record of a user. Returns the number removed."""
        with self._connection() as conn:
            cur = conn.execute(
                "DELETE FROM bmi_records WHERE username = ? COLLATE NOCASE", (username,)
            )
            return cur.rowcount


def export_records_to_csv(records, path):
    """Write records to a CSV file (Excel friendly). Returns the row count.

    Raises OSError / csv.Error on file problems; the GUI handles them.
    """
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_HEADERS)
        for r in records:
            writer.writerow([r["id"], r["username"], f"{r['weight']:.2f}",
                             f"{r['height']:.2f}", f"{r['bmi']:.2f}",
                             r["category"], r["recorded_at"]])
    return len(records)
