from pathlib import Path
import sqlite3

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


app = FastAPI()

DATABASE_PATH = Path(__file__).with_name("tasks.db")

tasks = [
    {
        "id": 1,
        "title": "Learn FastAPI",
        "done": False,
    },
    {
        "id": 2,
        "title": "Build API",
        "done": False,
    },
    {
        "id": 3,
        "title": "Upload Github",
        "done": True,
    },
]


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def task_to_dict(task_row):
    return {
        "id": task_row["id"],
        "title": task_row["title"],
        "done": bool(task_row["done"]),
    }


def initialize_database():
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        task_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

        if task_count == 0:
            connection.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [
                    ("Learn FastAPI", 0),
                    ("Build API", 0),
                    ("Upload Github", 1),
                ],
            )


initialize_database()


@app.exception_handler(HTTPException)
def handle_http_exception(_, exc):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = {"error": exc.detail["error"]}
    else:
        content = {"error": str(exc.detail)}

    return JSONResponse(status_code=exc.status_code, content=content)


class TaskCreate(BaseModel):
    title:str
class TaskUpdate(BaseModel):
    title:str
    done:bool
    
@app.get("/")
def home():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": [
            "/tasks"
        ]
    }

@app.get("/health")
def health():
    return {
        "status":"ok"
    }
    
@app.get("/tasks")
def get_tasks():
    with get_db_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, done FROM tasks ORDER BY id"
        ).fetchall()

    return [task_to_dict(row) for row in rows]


@app.get("/tasks/{id}")
def get_task(id:int):
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (id,),
        ).fetchone()

    if row is not None:
        return task_to_dict(row)

    raise HTTPException(
        status_code=404,
        detail={"error": "Task not found"}
    )
    
    
@app.post("/tasks",status_code=201)
def create_task(task:TaskCreate):

    if not task.title.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": "Title cannot be empty"}
        )

    with get_db_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            (task.title, 0),
        )
        created_task = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return task_to_dict(created_task)

@app.put("/tasks/{id}")
def update_task(id:int,data:TaskUpdate):

    if not data.title.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": "Title cannot be empty"}
        )

    for task in tasks:

        if task["id"] == id:

            task["title"] = data.title
            task["done"] = data.done

            return task


    raise HTTPException(
        status_code=404,
        detail={"error": "Task not found"}
    )
    
@app.delete("/tasks/{id}",status_code=204)
def delete_task(id:int):

    for task in tasks:

        if task["id"] == id:

            tasks.remove(task)

            return


    raise HTTPException(
        status_code=404,
        detail={"error": "Task not found"}
    )