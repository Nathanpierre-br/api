from re import search
from time import time as timestamp

from fastapi import APIRouter, Request

from helpers.database.models import Global, ModelFabric
from helpers.database.mongo import Database
from helpers.generator import Generator
from helpers.routers.cachable import CachableRoute
from objects import Base, Errors, Links

links = APIRouter()
links.route_class = CachableRoute


@links.post("/g/s/link-resolution")
@links.post("/g/s-x{ndcId}/link-resolution")
@links.post("/x{ndcId}/s/link-resolution")
@links.post("/g/s/link-translation")
@links.post("/g/s-x{ndcId}/link-translation")
@links.post("/x{ndcId}/s/link-translation")
async def make_link(request: Request, ndcId: int = 0):
    t1 = timestamp()
    data = await request.json()

    db = await Database().init()
    links_table = db.get(table="Links")

    if data["objectType"] == 0:
        if str(ndcId) in request.url.path:
            check_table = db.get(f"x{ndcId}", "Users")
        else:
            check_table = db.get(table="Users")
    elif data["objectType"] == 1:
        check_table = db.get(f"x{ndcId}", "Blogs")
    elif data["objectType"] == 12:
        check_table = db.get(f"x{ndcId}", "Chats")
    elif data["objectType"] == 15:
        check_table = db.get(f"x{ndcId}", "Communities")
    else:
        db.close()
        return Errors.UnimplementedPath(timestamp() - t1)

    check = await check_table.find_one({"id": data["objectId"]})
    if check is None:
        db.close()
        return Errors.MythicData(timestamp() - t1)

    link = await links_table.find_one(
        {"objectId": data["objectId"], "objectType": data["objectType"], "ndcId": ndcId}
    )

    if link is None:
        link = ModelFabric.Construct(
            Global.Links,
            code=(
                check["aminoId"]
                if data["objectType"] == 0 and ndcId == 0
                else Generator.RealString(8)
            ),
            targetCode=data.get("targetCode", 1),
            objectId=data["objectId"],
            objectType=data["objectType"],
            ndcId=ndcId,
        )
        await links_table.insert_one(link)
    db.close()

    if data["objectType"] == 0:
        return Base.Answer(Links.User(link), spent_time=timestamp() - t1)
    elif data["objectType"] == 1:
        return Base.Answer(Links.Blog(link), spent_time=timestamp() - t1)
    elif data["objectType"] == 12:
        return Base.Answer(Links.Chat(link), spent_time=timestamp() - t1)
    elif link["objectType"] == 15:
        return Base.Answer(Links.Community(link), spent_time=timestamp() - t1)


@links.get("/g/s/link-resolution")
@links.get("/x{ndcId}/s/link-resolution")
@links.get("/g/s/link-translation")
@links.get("/x{ndcId}/s/link-translation")
@links.get("/g/s/link-identify")
@links.get("/x{ndcId}/s/link-identify")
async def resolute_link(request: Request, q: str, ndcId: int = 0):
    t1 = timestamp()

    db = await Database().init()
    links_table = db.get(table="Links")

    """q = (
        q.replace("http://aminoapps.com/", "http://altamino.top/")
        .replace("https://aminoapps.com/", "http://altamino.top/")
        .replace("http://altamino.top/u/", "")
        .replace("http://altamino.top/p/", "")
        .replace("http://altamino.top/c/", "")
    )"""

    match = search(r"(http|https):\/\/altamino.top\/(?P<type>.*)\/(?P<code>.*)", q)
    if match is None:
        return Errors.InvalidRequest(timestamp() - t1)

    code_type, query = match.group("type"), match.group("code")
    if code_type == "c":
        cum_table = db.get(table="Communities")
        cum_data = await cum_table.find_one({"aminoId": query})
        if cum_data is None:
            return Errors.DataNotExist(timestamp() - t1)

        db.close()
        return Base.Answer(
            Links.Community(
                {
                    "objectType": 15,
                    "ndcId": cum_data.get("id"),
                    "code": query,
                    "objectId": str(cum_data.get("id")),
                }
            ),
            spent_time=timestamp() - t1,
        )
    else:
        link = await links_table.find_one({"code": query})
        if link is None and code_type == "u":
            gl_users_table = db.get(table="Users")
            link = await gl_users_table.find_one({"aminoId": query})
            if link is None:
                return Errors.DataNotExist(timestamp() - t1)

            return Base.Answer(
                Links.User(
                    {
                        "objectType": 0,
                        "ndcId": 0,
                        "code": query,
                        "objectId": str(link.get("id")),
                    }
                ),
                spent_time=timestamp() - t1,
            )

        db.close()
        if link is None:
            return Errors.DataNotExist(timestamp() - t1)

        if link["objectType"] == 0:
            return Base.Answer(Links.User(link), spent_time=timestamp() - t1)
        elif link["objectType"] == 1:
            return Base.Answer(Links.Blog(link), spent_time=timestamp() - t1)
        elif link["objectType"] == 12:
            return Base.Answer(Links.Chat(link), spent_time=timestamp() - t1)
