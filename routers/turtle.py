from cloudstile import AsyncTurnstile
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from helpers.config import Config
from helpers.processors.cache import CacheProcessor
from objects.turtle import TurtleAnswers

turtle = APIRouter()
turnstile = AsyncTurnstile(Config.TURNSTILE_TOKEN)
templates = Jinja2Templates(directory="templates")


# GET /turtle/hello - serve the captcha page
@turtle.get("/turtle/hello")
async def turnstile_page(request: Request, inspector: str = None):
    if inspector:
        return templates.TemplateResponse(
            request=request, name="captcha.html", context={"inspector": inspector}
        )
    return templates.TemplateResponse(request=request, name="error.html")


# POST /turtle/validate - validate the captcha
@turtle.post("/turtle/validate")
@turtle.post("/turtle/validate/{why}")
async def turnstile_validation(request: Request, why: str = None):
    data = await request.json()
    turtle, inspector = data["turtle"], data["inspector"]

    response = await turnstile.validate(turtle)
    if response.cdata != data["inspector"]:
        return TurtleAnswers.ERR("You can't get another inspector.")

    turtle = CacheProcessor.Get(inspector, prefix="turtlelimiter:")
    if turtle is None:
        return TurtleAnswers.ERR("This inspector have no case in their hands.")

    if why == "email":
        CacheProcessor.Update(inspector, value="OK", prefix="turtlelimiter:")
    else:
        CacheProcessor.Delete(inspector, prefix="turtlelimiter:")

    return TurtleAnswers.OK()
