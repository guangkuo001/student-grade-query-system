from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "grades.db"

app = Flask(__name__)
_db_initialized = False


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            score INTEGER NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
        """
    )

    cur.execute("SELECT COUNT(*) AS cnt FROM students")
    count = cur.fetchone()["cnt"]

    if count == 0:
        students = [
            ("2026001", "张三"),
            ("2026002", "李四"),
            ("2026003", "王五"),
        ]
        scores = [
            ("2026001", "语文", 92),
            ("2026001", "数学", 88),
            ("2026001", "英语", 95),
            ("2026002", "语文", 76),
            ("2026002", "数学", 81),
            ("2026002", "英语", 79),
            ("2026003", "语文", 85),
            ("2026003", "数学", 90),
            ("2026003", "英语", 87),
        ]

        cur.executemany(
            "INSERT INTO students (student_id, name) VALUES (?, ?)", students
        )
        cur.executemany(
            "INSERT INTO scores (student_id, subject, score) VALUES (?, ?, ?)", scores
        )

    conn.commit()
    conn.close()


def ensure_db_initialized() -> None:
    global _db_initialized
    if _db_initialized:
        return

    # In serverless environments (for example Vercel), filesystem may be read-only.
    # If init fails there, we still allow read-only querying against bundled DB file.
    try:
        init_db()
    except sqlite3.OperationalError:
        pass
    _db_initialized = True


@app.route("/")
def home():
    ensure_db_initialized()
    return render_template("index.html")


@app.route("/api/query", methods=["GET"])
def query_scores():
    ensure_db_initialized()
    student_id = request.args.get("student_id", "").strip()
    if not student_id:
        return jsonify({"error": "请先输入学号"}), 400

    conn = get_db_connection()
    student = conn.execute(
        "SELECT student_id, name FROM students WHERE student_id = ?",
        (student_id,),
    ).fetchone()

    if student is None:
        conn.close()
        return jsonify({"error": "未找到该学号对应的学生"}), 404

    score_rows = conn.execute(
        "SELECT subject, score FROM scores WHERE student_id = ? ORDER BY subject",
        (student_id,),
    ).fetchall()
    conn.close()

    scores = [{"subject": row["subject"], "score": row["score"]} for row in score_rows]
    average = round(sum(item["score"] for item in scores) / len(scores), 2) if scores else 0

    return jsonify(
        {
            "student_id": student["student_id"],
            "name": student["name"],
            "scores": scores,
            "average": average,
        }
    )


if __name__ == "__main__":
    ensure_db_initialized()
    app.run(debug=True)
