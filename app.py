from __future__ import annotations

import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, render_template, request

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # Local sqlite mode can run without psycopg.
    psycopg = None
    dict_row = None


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "grades.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith(
    "postgresql://"
)

app = Flask(__name__)
_db_initialized = False
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()


def get_db_connection():
    if IS_POSTGRES:
        if psycopg is None:
            raise RuntimeError("Missing dependency: psycopg")
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def auth_required(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        if not ADMIN_TOKEN:
            return handler(*args, **kwargs)
        header_token = request.headers.get("X-Admin-Token", "").strip()
        if header_token != ADMIN_TOKEN:
            return jsonify({"error": "管理员认证失败"}), 401
        return handler(*args, **kwargs)

    return wrapper


def init_db() -> None:
    conn = get_db_connection()
    cur = conn.cursor()

    if IS_POSTGRES:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                student_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                id SERIAL PRIMARY KEY,
                student_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                score INTEGER NOT NULL,
                UNIQUE (student_id, subject),
                FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
            )
            """
        )
        cur.execute("SELECT COUNT(*) AS cnt FROM students")
        count = cur.fetchone()["cnt"]
    else:
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
                UNIQUE(student_id, subject),
                FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
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

        if IS_POSTGRES:
            cur.executemany(
                "INSERT INTO students (student_id, name) VALUES (%s, %s)", students
            )
            cur.executemany(
                "INSERT INTO scores (student_id, subject, score) VALUES (%s, %s, %s)",
                scores,
            )
        else:
            cur.executemany(
                "INSERT INTO students (student_id, name) VALUES (?, ?)", students
            )
            cur.executemany(
                "INSERT INTO scores (student_id, subject, score) VALUES (?, ?, ?)",
                scores,
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
    cur = conn.cursor()
    if IS_POSTGRES:
        cur.execute(
            "SELECT student_id, name FROM students WHERE student_id = %s",
            (student_id,),
        )
    else:
        cur.execute(
            "SELECT student_id, name FROM students WHERE student_id = ?",
            (student_id,),
        )
    student = cur.fetchone()

    if student is None:
        conn.close()
        return jsonify({"error": "未找到该学号对应的学生"}), 404

    if IS_POSTGRES:
        cur.execute(
            "SELECT subject, score FROM scores WHERE student_id = %s ORDER BY subject",
            (student_id,),
        )
    else:
        cur.execute(
            "SELECT subject, score FROM scores WHERE student_id = ? ORDER BY subject",
            (student_id,),
        )
    score_rows = cur.fetchall()
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


@app.route("/api/admin/student", methods=["POST"])
@auth_required
def add_student():
    ensure_db_initialized()
    data = request.get_json(silent=True) or {}
    student_id = str(data.get("student_id", "")).strip()
    name = str(data.get("name", "")).strip()

    if not student_id or not name:
        return jsonify({"error": "student_id 和 name 不能为空"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if IS_POSTGRES:
            cur.execute(
                "INSERT INTO students (student_id, name) VALUES (%s, %s)",
                (student_id, name),
            )
        else:
            cur.execute(
                "INSERT INTO students (student_id, name) VALUES (?, ?)",
                (student_id, name),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        return jsonify({"error": "新增学生失败（可能学号已存在）"}), 400

    conn.close()
    return jsonify({"message": "新增学生成功"})


@app.route("/api/admin/student/<student_id>", methods=["DELETE"])
@auth_required
def delete_student(student_id: str):
    ensure_db_initialized()
    conn = get_db_connection()
    cur = conn.cursor()
    if IS_POSTGRES:
        cur.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
    else:
        cur.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()

    if deleted == 0:
        return jsonify({"error": "学生不存在"}), 404
    return jsonify({"message": "删除学生成功"})


@app.route("/api/admin/score", methods=["POST"])
@auth_required
def add_score():
    ensure_db_initialized()
    data = request.get_json(silent=True) or {}
    student_id = str(data.get("student_id", "")).strip()
    subject = str(data.get("subject", "")).strip()
    score = data.get("score")

    if not student_id or not subject or score is None:
        return jsonify({"error": "student_id、subject、score 不能为空"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if IS_POSTGRES:
            cur.execute(
                "INSERT INTO scores (student_id, subject, score) VALUES (%s, %s, %s)",
                (student_id, subject, int(score)),
            )
        else:
            cur.execute(
                "INSERT INTO scores (student_id, subject, score) VALUES (?, ?, ?)",
                (student_id, subject, int(score)),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        return jsonify({"error": "新增成绩失败（学生不存在或科目已存在）"}), 400

    conn.close()
    return jsonify({"message": "新增成绩成功"})


@app.route("/api/admin/score", methods=["PUT"])
@auth_required
def update_score():
    ensure_db_initialized()
    data = request.get_json(silent=True) or {}
    student_id = str(data.get("student_id", "")).strip()
    subject = str(data.get("subject", "")).strip()
    score = data.get("score")

    if not student_id or not subject or score is None:
        return jsonify({"error": "student_id、subject、score 不能为空"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    if IS_POSTGRES:
        cur.execute(
            "UPDATE scores SET score = %s WHERE student_id = %s AND subject = %s",
            (int(score), student_id, subject),
        )
    else:
        cur.execute(
            "UPDATE scores SET score = ? WHERE student_id = ? AND subject = ?",
            (int(score), student_id, subject),
        )
    updated = cur.rowcount
    conn.commit()
    conn.close()

    if updated == 0:
        return jsonify({"error": "未找到对应成绩记录"}), 404
    return jsonify({"message": "更新成绩成功"})


@app.route("/api/admin/score", methods=["DELETE"])
@auth_required
def delete_score():
    ensure_db_initialized()
    student_id = request.args.get("student_id", "").strip()
    subject = request.args.get("subject", "").strip()
    if not student_id or not subject:
        return jsonify({"error": "请提供 student_id 和 subject"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    if IS_POSTGRES:
        cur.execute(
            "DELETE FROM scores WHERE student_id = %s AND subject = %s",
            (student_id, subject),
        )
    else:
        cur.execute(
            "DELETE FROM scores WHERE student_id = ? AND subject = ?",
            (student_id, subject),
        )
    deleted = cur.rowcount
    conn.commit()
    conn.close()

    if deleted == 0:
        return jsonify({"error": "未找到对应成绩记录"}), 404
    return jsonify({"message": "删除成绩成功"})


if __name__ == "__main__":
    ensure_db_initialized()
    app.run(debug=True)
