from fastapi import FastAPI, Request, Response, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlmodel import SQLModel, create_engine, Field, Session, select
from typing import Optional
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    
class Todo(SQLModel, table=True):
    id:Optional[int] = Field(default=None, primary_key=True)
    task: str
    user_id: int = Field(foreign_key='user.id', index=True)    

app=FastAPI()

engine=create_engine('sqlite:///db.sqlite3', echo=True)

app.add_middleware(
    SessionMiddleware,
    secret_key='secret_key',
    session_cookie='session',
    https_only=False,
    same_site='lax',
)

pwd_context=CryptContext(schemes=['bcrypt'], deprecated='auto')

def hash_password(pw):
    return pwd_context.hash(pw)

def verify_password(pw, hashed):
    return pwd_context.verify(pw,hashed)

templates = Jinja2Templates(directory='templates')

@app.get('/login')
def login_page(request: Request):
    return templates.TemplateResponse('login.html',{'request':request})

@app.post('/login')
def login(request: Request, email: str=Form(...), password: str=Form(...)):
    with Session(engine) as session:
        user=session.exec(select(User).where(User.email==email)).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse('login.html',{'request':request,'error':'Invalid email or passwoed'})
    
    request.session['user_id']=user.id
    return RedirectResponse(url='/', status_code=303)

@app.post('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/login',status_code=303) 

def get_current_user(request: Request):
    user_id=request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401)
    return user_id

@app.get('/')
def index(request: Request):
    user_id=request.session.get('user_id')
    if not user_id:
        return RedirectResponse('/login',status_code=303)

    with Session(engine) as session:
        task_list=session.exec(select(Todo).where(Todo.user_id==user_id)).all()
        
    return templates.TemplateResponse('task.html',{'request':request, 'task_list':task_list})

@app.post('/task/submit')
def add_task(request: Request, task: str=Form(...)):
    user_id=request.session.get('user_id')
    todo=Todo(task=task,user_id=user_id)
    with Session(engine) as session:
        session.add(todo)
        session.commit()
        task_list=session.exec(select(Todo).where(user_id==user_id)).all()
    return templates.TemplateResponse('task_list_fragment.html',{'request':request,'task_list':task_list})


@app.delete('/task/{task_id}')
def delete_task(request: Request, task_id: int):
    user_id=get_current_user(request)
    with Session(engine) as session:
        todo=session.exec(select(Todo).where(Todo.user_id==user_id, Todo.id==task_id)).first()
        
        if not todo:
            raise HTTPException(status_code=404, detail='Tasjk not found')

        session.delete(todo)
        session.commit()

        todo_list=session.exec(select(Todo).where(Todo.user_id==user_id)).all()
    
    return templates.TemplateResponse('task_list_fragment.html',{'request':request,'task_list':todo_list})

@app.get("/task/{task_id}/edit")
def edit_task_form(request: Request, task_id: int):
    user_id = get_current_user(request)
    with Session(engine) as session:
        todo = session.exec(
            select(Todo).where((Todo.id == task_id) & (Todo.user_id == user_id))
        ).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    return templates.TemplateResponse(
        "task_edit_fragment.html",
        {"request": request, "todo": todo}
    )

@app.patch('/task/{task_id}/update')
def update_task(request:Request,task_id: int, task: str=Form(...)):
    user_id=get_current_user(request)
    with Session(engine) as session:
        todo=session.exec(select(Todo).where(Todo.id==task_id, Todo.user_id==user_id)).first()
        if not todo:
            raise HTTPException(status_code=404,detail='Todo not found')
        todo.task=task
        session.add(todo)
        session.commit()
        
        task_list=session.exec(select(Todo).where(Todo.user_id==user_id)).all()
        
    return templates.TemplateResponse('task_list_fragment.html',{"request":request,'task_list':task_list})
    
def create_admin_if_needed():
    with Session(engine) as session:
        exists = session.exec(select(User).where(User.email=="admin@example.com")).first()
        if not exists:
            u = User(email="admin@example.com", password_hash=hash_password("pass"))
            session.add(u)
            session.commit()

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    create_admin_if_needed()