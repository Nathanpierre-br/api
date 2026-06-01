# import

from brotli_asgi import BrotliMiddleware
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse, RedirectResponse

from objects import Errors
from routers.blogs import blog_methods
from routers.chats import chats
from routers.communities import communities
from routers.configurations import configurations
from routers.links import links
from routers.logregin import logregin

# routers
from routers.mock import mock
from routers.moderation_tools import moderation_tools
from routers.profile import profile_methods
from routers.pseudoacm import pseudoacm
from routers.turtle import turtle
from routers.upload_media import upload_media
from routers.acm import acm_router

# app things

app = FastAPI(title="AltAmino", version="1", docs_url=None, redoc_url=None)


@app.get("/")
async def redirect():
    return RedirectResponse("https://altamino.top")


@app.get("/health")
async def health():
    return {"alive": True}


app.include_router(mock, prefix="/api/v1")
app.include_router(chats, prefix="/api/v1")
app.include_router(turtle, prefix="/api/v1")
app.include_router(links, prefix="/api/v1")
app.include_router(logregin, prefix="/api/v1")
app.include_router(upload_media, prefix="/api/v1")
app.include_router(configurations, prefix="/api/v1")
app.include_router(profile_methods, prefix="/api/v1")
app.include_router(communities, prefix="/api/v1")
app.include_router(blog_methods, prefix="/api/v1")
app.include_router(moderation_tools, prefix="/api/v1")
app.include_router(pseudoacm, prefix="/api/v1")
app.include_router(acm_router, prefix="/api/v1")

app.add_middleware(BrotliMiddleware, gzip_fallback=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(403)
@app.exception_handler(422)
async def custom_403_handler(_, __):
    return Errors.Forbidden()


@app.exception_handler(404)
@app.exception_handler(405)
async def custom_404_handler(_, __):
    print("No path like: ", _.url.path, "(", await _.body(), ") | ", __)
    return Errors.InvalidPath()


@app.exception_handler(RequestValidationError)
async def custom_422_handler(_, exc: RequestValidationError):
    print(exc.errors())
    return Errors.CantProcessData()


@app.exception_handler(500)
async def custom_500_handler(_, __):
    try:
        if isinstance(__.args[0], ORJSONResponse) or isinstance(
            __.args[0], JSONResponse
        ):
            return __.args[0]
    except Exception:
        print("Not a status code that we returned!")

    try:
        print("What happened:", _, "//", __)
    except Exception:
        print("WE CAN'T EVEN DUCKING PRINT WHAT HAPPENED. COOL")

    return Errors.InternalServerError()
