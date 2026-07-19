from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A simple CRUD To-Do API built with FastAPI"
)


# In-memory database
tasks = [
    {
        "id": 1,
        "title": "Learn FastAPI",
        "done": False
    },
    {
        "id": 2,
        "title": "Build API",
        "done": False
    },
    {
        "id": 3,
        "title": "Upload Github",
        "done": True
    }
]


# Request models
class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str
    done: bool


# Root endpoint
@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": [
            "/tasks",
            "/tasks/{id}"
        ]
    }


# Health endpoint
@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# Get all tasks
@app.get("/tasks")
def get_tasks():
    return tasks


# Get single task
@app.get("/tasks/{id}")
def get_task(id: int):

    for task in tasks:
        if task["id"] == id:
            return task

    raise HTTPException(
        status_code=404,
        detail={
            "error": f"Task {id} not found"
        }
    )


# Create task
@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):

    if not task.title.strip():

        raise HTTPException(
            status_code=400,
            detail={
                "error": "Title cannot be empty"
            }
        )


    new_task = {
        "id": len(tasks) + 1,
        "title": task.title,
        "done": False
    }


    tasks.append(new_task)

    return new_task



# Update task
@app.put("/tasks/{id}")
def update_task(id: int, updated_task: TaskUpdate):

    for task in tasks:

        if task["id"] == id:

            if not updated_task.title.strip():

                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Title cannot be empty"
                    }
                )


            task["title"] = updated_task.title
            task["done"] = updated_task.done

            return task


    raise HTTPException(
        status_code=404,
        detail={
            "error": f"Task {id} not found"
        }
    )



# Delete task
@app.delete("/tasks/{id}", status_code=204)
def delete_task(id: int):

    for task in tasks:

        if task["id"] == id:

            tasks.remove(task)

            return None


    raise HTTPException(
        status_code=404,
        detail={
            "error": f"Task {id} not found"
        }
    )