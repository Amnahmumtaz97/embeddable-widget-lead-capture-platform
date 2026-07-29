import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
DB_PATH = Path(__file__).with_name("tasks.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

        if task_count == 0:
            with conn:
                conn.executemany(
                    "INSERT INTO tasks (title, done) VALUES (?, ?)",
                    [
                        ("Learn FastAPI", 0),
                        ("Build API", 0),
                        ("Upload Github", 1),
                    ],
                )


init_db()


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str
    done: bool


def row_to_task(row):
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.get("/tasks")
def list_tasks():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return [row_to_task(row) for row in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})

    return row_to_task(row)


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail={"error": "Title cannot be empty"})

    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            (task.title, 0),
        )
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return row_to_task(row)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail={"error": "Title cannot be empty"})

    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (task.title, int(task.done), task_id),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail={"error": "Task not found"})

        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    return row_to_task(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})
