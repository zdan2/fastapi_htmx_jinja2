from fastapi import FastAPI, Request, Form  # Formを追加インポート
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory='templates')

task_list = []

@app.get('/')
def index(request: Request):
    return templates.TemplateResponse('task.html', {'request': request, 'task_list': task_list})

@app.post('/task/submit')
async def create_task(request: Request, task: str = Form(...)):
    task_list.append(task)
    
    return templates.TemplateResponse('task_list_fragment.html', {'request': request, 'task_list': task_list})