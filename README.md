# Task API

A simple CRUD to-do API built with **FastAPI** and **SQLite**.

This version keeps the same API as the in-memory assignment, but task data now lives in a database file so it survives restarts.

## Why SQLite

SQLite was a good fit for this assignment because it is lightweight, requires no separate server, and creates a single `tasks.db` file automatically when the app starts.

## Where the database lives

The database file is stored next to `main.py` as `tasks.db`.

## How to run

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The app creates `tasks.db` and the `tasks` table automatically on first run, then inserts three sample tasks only when the table is empty. The database file is git-ignored so each fresh clone can create its own local copy.

## Example SQL

```sql
SELECT * FROM tasks WHERE done = 1;
```

This query returns only the completed tasks from the `tasks` table.

## Database viewer screenshot

Add a screenshot here after opening `tasks.db` in DB Browser for SQLite.

## API

- `GET /tasks`
- `GET /tasks/{id}`
- `POST /tasks`
- `PUT /tasks/{id}`
- `DELETE /tasks/{id}`