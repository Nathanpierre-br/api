from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

static_things = APIRouter()
templates = Jinja2Templates(directory="templates")


@static_things.get("/static")
async def static_catcher(request: Request):
    return templates.TemplateResponse(request=request, name="change_password.html")
