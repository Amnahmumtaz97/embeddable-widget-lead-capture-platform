from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from pydantic import BaseModel

from storage import TaskRepository


app = FastAPI()
repository = TaskRepository()


@app.on_event("startup")
def initialize_database():
    repository.initialize()


@app.exception_handler(HTTPException)
def handle_http_exception(_, exc):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = {"error": exc.detail["error"]}
    else:
        content = {"error": str(exc.detail)}

    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(RequestValidationError)
def handle_validation_error(_, __):
    return JSONResponse(status_code=400, content={"error": "Invalid request body"})


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str
    done: bool


@app.get("/")
def home():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks():
    return repository.list_tasks()


@app.get("/tasks/{id}")
def get_task(id: int):
    task = repository.get_task(id)

    if task is not None:
        return task

    raise HTTPException(status_code=404, detail={"error": "Task not found"})


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail={"error": "Title cannot be empty"})

    return repository.create_task(task.title)


@app.put("/tasks/{id}")
def update_task(id: int, data: TaskUpdate):
    if not data.title.strip():
        raise HTTPException(status_code=400, detail={"error": "Title cannot be empty"})

    updated_task = repository.update_task(id, data.title, data.done)

    if updated_task is not None:
        return updated_task

    raise HTTPException(status_code=404, detail={"error": "Task not found"})


@app.delete("/tasks/{id}", status_code=204)
def delete_task(id: int):
    deleted = repository.delete_task(id)

    if not deleted:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})

    return Response(status_code=204)