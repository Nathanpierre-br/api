from base64 import b85encode, b85decode
from re import compile as regex_compile
from re import IGNORECASE as RE_IGNORECASE
from fastapi import APIRouter, Request
from time import time as timestamp

# import sys
# sys.path.append('../')
from objects import *
from helpers.config import Config
from helpers.database.mongo import *
from helpers.routers.cachable import CachableRoute

communities = APIRouter()
communities.route_class = CachableRoute


# communities search
@communities.get("/g/s/community/search")
async def search_community(
    request: Request, q: str = "", size: int = 25, pageToken: str | None = None
):
    t1 = timestamp()
    size = size if 0 > size > 101 else 25

    # parse page token
    if pageToken:
        try:
            start = int(b85decode(pageToken).decode())
        except:
            start = 0
    else:
        start = 0

    db = await Database().init()
    table = await db.get("x0", "Communities")

    query = {"name": regex_compile(r"{}".format(q), RE_IGNORECASE)}
    items = [item async for item in table.find(query).skip(start).limit(size)]
    if len(items) > 0:
        return Base.Answer(
            {
                "communityList": [await Community.Info(item["id"], db) for item in items],
                "paging": {
                    "nextPageToken": b85encode(str(size + start).encode()).decode(),
                    "prevPageToken": b85encode(
                        ("0" if start - size <= 0 else str(start - size)).encode()
                    ).decode(),
                },
                "allItemCount": len(items),
            },
            spent_time=timestamp() - t1,
        )

    return Base.Answer({"communityList": [], "paging": {}, "allItemCount": 0})


# community join
@communities.post("/x{ndcId}/s/community/join")
async def join_community(
    request: Request, ndcId: int
):
    t1 = timestamp()

    # db = await Database().init()

    # todo

    return Base.Answer({}, spent_time=timestamp()-t1)

# community leave
@communities.post("/x{ndcId}/s/community/leave")
async def leave_community(
    request: Request, ndcId: int
):
    t1 = timestamp()

    # db = await Database().init()

    # todo

    return Base.Answer({}, spent_time=timestamp()-t1)
