from fastapi import APIRouter, Request
from time import time as timestamp

from objects import Errors, Base
from helpers.routers.cachable import CachableRoute


from helpers.database.mongo import Database

acm_router = APIRouter()
acm_router.route_class = CachableRoute




@acm_router.post("/g/s/community")
async def create_community(request: Request):
    t1 = timestamp()

    data = await request.json()

    name = data.get("name")
    tagline = data.get("tagline")
    icon = data.get("icon")
    theme_color = data.get("themeColor")
    join_type = data.get("joinType", 0)
    primary_language = data.get("primaryLanguage", "en")

    if not name or not tagline or not icon or not theme_color:
        return Errors.InvalidRequest(timestamp() - t1)



    required_icon_fields = ["height", "width", "x", "y", "imageMatrix", "path"]
    if not all(k in icon for k in required_icon_fields):
        return Errors.InvalidRequest(timestamp() - t1)


    db = await Database().init()
    # -------- 5. RETURN --------
    return Base.Answer(
        spent_time=timestamp() - t1,
        data={}
    )
