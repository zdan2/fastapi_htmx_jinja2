from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional

app = FastAPI()

templates = Jinja2Templates(directory="templates")


class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task: str


engine = create_engine("sqlite:///db.sqlite3", echo=False)


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


@app.get("/")
def index(request: Request):
    with Session(engine) as session:
        task_list = session.exec(select(Todo)).all()
    return templates.TemplateResponse(
        "task.html", {"request": request, "task_list": task_list}
    )


@app.post("/task/submit")
def create_task(request: Request, task: str = Form(...)):
    todo = Todo(task=task)
    with Session(engine) as session:
        session.add(todo)
        session.commit()
        session.refresh(todo)
        task_list = session.exec(select(Todo)).all()
    return templates.TemplateResponse(
        "task_list_fragment.html", {"request": request, "task_list": task_list}
    )


@app.delete("/task/{todo_id}")
def delete_task(request: Request, todo_id: int):
    with Session(engine) as session:
        task = session.get(Todo, todo_id)
        if task:
            session.delete(task)
            session.commit()
        task_list = session.exec(select(Todo)).all()
    return templates.TemplateResponse(
        "task_list_fragment.html", {"request": request, "task_list": task_list}
    )
