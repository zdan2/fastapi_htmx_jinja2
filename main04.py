from fastapi import FastAPI, Request, Form
from sqlmodel import SQLModel, Field, create_engine
from typing import Optional
from starlette.middleware.sessions import SessionMiddleware


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None,primary_key=True)
    email: str =Field(index=True, unique=True)
    password_hash: str
    

app=FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key='CHANGE_ME_TO_RANDOM_LONG_SECRET',
    session_cookie='session',
    https_only=False,
    same_site='lax',
)

from passlib.context import CryptContext

pwd_context=CryptContext(schemes=['bcrypt'], deprecated='auto')

def hash_password(pw: str):
    return pwd_context.hash(pw)

def verify_password(pw: str, hashed: str):
    return pwd_context.verify(pw, hashed)

from fastapi.responses import RedirectResponse,Response
from sqlmodel import Session, select
from fastapi.templating import Jinja2Templates

templates=Jinja2Templates(directory='templates')

engine=create_engine('sqlite:///db.sqlite3',echo=False)

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    create_admin_if_needed()

@app.get("/")
def index(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    # ここでタスク一覧などを返す
    return templates.TemplateResponse("task.html", {"request": request})

@app.get('/login')
def login_page(request: Request):
    return templates.TemplateResponse('login.html',{'request':request})

@app.post('/login')
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
    
    if not user or not verify_password(password,user.password_hash):
        return templates.TemplateResponse('login_form_fragment.html',{'request':request, 'error':'invalid password or email'})
    
    request.session['user_id']=user.id
    
    resp = Response(status_code=204)
    resp.headers["HX-Redirect"] = "/"
    return resp

@app.post('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/login',status_code=303)



def create_admin_if_needed():
    with Session(engine) as session:
        exists = session.exec(select(User).where(User.email=="admin@example.com")).first()
        if not exists:
            u = User(email="admin@example.com", password_hash=hash_password("AdminPassw0rd!"))
            session.add(u)
            session.commit()