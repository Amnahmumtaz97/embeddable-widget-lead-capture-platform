# Task API

A simple CRUD to-do API built with **FastAPI** and **Postgres**.

The routes stay the same, but the storage layer now uses a Postgres repository instead of the old in-memory approach. That is the only architectural swap: the API contract is unchanged.

## How to run the full stack

1. Copy `.env.example` to `.env` and adjust the values if needed.
2. Run `docker compose up --build`.
3. Open the app at `http://localhost:8000`.

Postgres runs in Docker with a named volume, so the task data survives container restarts.

## What lives where

- `main.py` keeps the FastAPI routes and validation.
- `storage.py` contains the Postgres repository.
- `db/init.sql` creates the `tasks` table.
- `docker-compose.yml` starts the app and database together.

## Persistence check

To prove persistence, I created a task through `POST /tasks`, restarted the app container, and then called `GET /tasks` again. The new row was still present because the database state lives in the named Docker volume.

## API

- `GET /tasks`
- `GET /tasks/{id}`
- `POST /tasks`
- `PUT /tasks/{id}`
- `DELETE /tasks/{id}`

## Notes

- Validation errors return `400` with JSON error bodies.
- Missing tasks return `404` with `{"error": "Task not found"}`.
- The Postgres schema is created from `db/init.sql`, and the app seeds three starter tasks only when the table is empty.
