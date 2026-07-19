# Task API

FastAPI CRUD API.

## Run

Install:

pip install -r requirements.txt


Start:

uvicorn main:app --reload


## Endpoints

|Method|URL|
|-|-|
|GET|/tasks|
|GET|/tasks/{id}|
|POST|/tasks|
|PUT|/tasks/{id}|
|DELETE|/tasks/{id}|


Swagger:

http://localhost:8000/docs