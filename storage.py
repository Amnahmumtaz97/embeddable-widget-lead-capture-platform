from pathlib import Path
import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "db" / "init.sql"
DEFAULT_DATABASE_URL = "postgresql://todo_user:todo_password@db:5432/todo_api"
SEED_TASKS = [
    ("Learn FastAPI", False),
    ("Build API", False),
    ("Upload Github", True),
]


def task_to_dict(task_row):
    return {
        "id": task_row["id"],
        "title": task_row["title"],
        "done": bool(task_row["done"]),
    }


class TaskRepository:
    def __init__(self, database_url=None):
        self.database_url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

    def connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def initialize(self):
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(schema_sql)
                cursor.execute("SELECT COUNT(*) AS count FROM tasks")
                task_count = cursor.fetchone()["count"]

                if task_count == 0:
                    cursor.executemany(
                        "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                        SEED_TASKS,
                    )

    def list_tasks(self):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, title, done FROM tasks ORDER BY id")
                rows = cursor.fetchall()

        return [task_to_dict(row) for row in rows]

    def get_task(self, task_id):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, title, done FROM tasks WHERE id = %s",
                    (task_id,),
                )
                row = cursor.fetchone()

        return task_to_dict(row) if row is not None else None

    def create_task(self, title):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
                    (title, False),
                )
                row = cursor.fetchone()

        return task_to_dict(row)

    def update_task(self, task_id, title, done):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
                    (title, done, task_id),
                )
                row = cursor.fetchone()

        return task_to_dict(row) if row is not None else None

    def delete_task(self, task_id):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))

                return cursor.rowcount > 0