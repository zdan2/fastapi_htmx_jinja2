from fastapi import FastAPI, Request, Form, Response, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlmodel import SQLModel, create_engine, Session, select, Field
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from typing import Optional
from datetime import datetime

app = FastAPI()

engine = create_engine("sqlite:///db.sqlite3", echo=True)

templates = Jinja2Templates(directory="templates")

app.add_middleware(
    SessionMiddleware,
    secret_key="seacret",
    session_cookie="session",
    https_only=False,
    same_site="lax",
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(pw):
    return pwd_context.hash(pw)


def verify_password(pw, hashed):
    return pwd_context.verify(pw, hashed)


def get_user_id(request: Request):
    user_id = request.session.get("user_id")
    return user_id


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    user_name: str = Field(index=True)


class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    create_date: datetime = Field(default_factory=datetime.now)
    task: str
    user_id: int = Field(foreign_key="user.id", index=True)


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()

        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse(
                "login_form_fragment.html",
                {"request": request, "error": "Invalid email or password"},
            )

    request.session["user_id"] = user.id
    response = Response(status_code=200)
    response.headers["HX-Redirect"] = "/"

    return response


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/")
def index(request: Request):
    user_id = get_user_id(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        task_list = session.exec(select(Todo).where(Todo.user_id == user_id)).all()

    return templates.TemplateResponse(
        "index.html", {"request": request, "task_list": task_list, "user": user}
    )


@app.post("/task/submit")
def add_task(request: Request, task: str = Form(...)):
    user_id = get_user_id(request)
    todo = Todo(task=task, user_id=user_id)

    with Session(engine) as session:
        session.add(todo)
        session.commit()

        task_list = session.exec(select(Todo).where(Todo.user_id == user_id)).all()

    return templates.TemplateResponse(
        "task_list_fragment.html", {"request": request, "task_list": task_list}
    )


@app.delete("/task/{task_id}")
def delete_task(request: Request, task_id: int):
    user_id = get_user_id(request)
    with Session(engine) as session:
        task = session.exec(
            select(Todo).where(Todo.user_id == user_id, Todo.id == task_id)
        ).first()
        if not task:
            raise HTTPException(status_code=404)

        session.delete(task)
        session.commit()

        task_list = session.exec(select(Todo).where(Todo.user_id == user_id)).all()

    return templates.TemplateResponse(
        "task_list_fragment.html", {"request": request, "task_list": task_list}
    )


@app.get("/task/{task_id}/edit")
def edit_task(request: Request, task_id: int):
    user_id = get_user_id(request)
    with Session(engine) as session:
        task = session.exec(
            select(Todo).where(Todo.id == task_id, Todo.user_id == user_id)
        ).first()

        if not task:
            raise HTTPException(status_code=404)

    return templates.TemplateResponse(
        "task_edit_fragment.html",
        {"request": request, "task_id": task_id, "todo": task},
    )


@app.patch("/task/{task_id}/update")
def update_task(request: Request, task_id: int, task: str = Form(...)):
    user_id = get_user_id(request)
    with Session(engine) as session:
        todo = session.exec(
            select(Todo).where(Todo.id == task_id, Todo.user_id == user_id)
        ).first()

        if not todo:
            raise HTTPException(status_code=404)

        todo.task = task
        session.add(todo)
        session.commit()

        task_list = session.exec(select(Todo).where(Todo.user_id == user_id)).all()

    return templates.TemplateResponse(
        "task_list_fragment.html", {"request": request, "task_list": task_list}
    )


@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    user_name: str = Form(...),
):
    email = email.strip().lower()
    if len(password) < 6:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "パスワードは６文字以上にしてください"},
        )
    with Session(engine) as session:

        exists = session.exec(select(User).where(User.email == email)).first()

        if exists:
            return templates.TemplateResponse(
                "register.html", {"request": request, "error": "すでに登録されています"}
            )
        user = User(
            email=email, password_hash=hash_password(password), user_name=user_name
        )
        session.add(user)
        session.commit()

    return RedirectResponse(url="/", status_code=303)


@app.get("/task/search")
def search_task(request: Request, q: str = Query(default="")):
    user_id = get_user_id(request)
    q = q.strip()

    with Session(engine) as session:
        stmt = select(Todo).where(Todo.user_id == user_id)

        if q:
            stmt = stmt.where(Todo.task.contains(q))
        task_list = session.exec(stmt).all()

        return templates.TemplateResponse(
            "task_list_fragment.html", {"request": request, "task_list": task_list}
        )


def create_admin_if_needed():
    with Session(engine) as session:
        exists = session.exec(
            select(User).where(User.email == "admin@example.com")
        ).first()
        if not exists:
            u = User(
                email="admin@example.com",
                password_hash=hash_password("pass"),
                user_name="admin",
            )
            session.add(u)
            session.commit()


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    create_admin_if_needed()
