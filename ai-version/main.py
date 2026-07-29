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
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.executemany(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        [
            ("Learn FastAPI", 0),
            ("Build API", 0),
            ("Upload Github", 1),
        ],
    )
    conn.commit()
    conn.close()


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
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [row_to_task(row) for row in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    conn = get_connection()
    row = conn.execute(f"SELECT * FROM tasks WHERE id = {task_id}").fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail={"error": f"Task {task_id} not found"})

    return row_to_task(row)


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail={"error": "Title cannot be empty"})

    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (task.title, 0),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    conn.close()
    return row_to_task(row)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail={"error": "Title cannot be empty"})

    conn = get_connection()
    cursor = conn.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (task.title, int(task.done), task_id),
    )
    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail={"error": f"Task {task_id} not found"})

    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return row_to_task(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail={"error": f"Task {task_id} not found"})
