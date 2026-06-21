from fastapi import APIRouter, Request

static_things = APIRouter()


@static_things.get("/static")
async def static_catcher(request: Request):
    print(request.headers)
    print(await request.body())

    return {"api:message": "Unknown route."}
