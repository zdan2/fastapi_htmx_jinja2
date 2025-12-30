from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import datetime

app=FastAPI()
templates=Jinja2Templates(directory='templates')

@app.get('/')
def page(request: Request):
    return templates.TemplateResponse('gettime.html',{'request':request})

@app.get('/button')
def get_time(request: Request):
    time=datetime.datetime.now()
    return templates.TemplateResponse(
        'time_fragment.html',{'request': request,'time':time}
    )