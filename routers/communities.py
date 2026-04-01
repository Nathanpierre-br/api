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


# get community info
# [GET] /g/s/community/{ndcId}


@communities.get("/g/s/community/{ndcId}")
async def get_community_info(ndcId: int, request: Request):
    t1 = timestamp()

    uid = request.state.session["uid"]

    db = await Database().init()
    info = await Communities.Info(ndcId, db, uid)
    await db.close()

    if not info:
        return Errors.CommunityNotFound(timestamp() - t1)

    return Base.Answer({"community": info}, spent_time=timestamp() - t1)


# communities you currently in
@communities.get("/g/s/community/joined")
async def joined_communities(request: Request, start: int = 0, size: int = 25):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Base.Answer(
            {
                "communityList": [],
                "userInfoInCommunities": {},
                "showStoreBadge": True,
            },
            spent_time=timestamp() - t1,
        )

    uid = request.state.session["uid"]
    size = size if 0 > size > 101 else 25

    db = await Database().init()
    table = await db.get(table="Users")
    row1 = await table.find_one({"id": uid})
    if row1 == None:
        return Errors.AccountNotExist(timestamp() - t1)

    table = await db.get(table="Communities")

    return Base.Answer(
        {
            "communityList": [
                await Communities.Info(item, db, uid)
                async for item in table.find(
                    {"id": {"$in": row1["communityList"][start:size]}}
                )
            ],
            "userInfoInCommunities": {},
            "showStoreBadge": True,
        },
        spent_time=timestamp() - t1,
    )


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
    table = await db.get(table="Communities")

    query = {"name": regex_compile(r"{}".format(q), RE_IGNORECASE)}
    items = [item async for item in table.find(query).skip(start).limit(size)]

    return Base.Answer(
        {
            "communityList": [await Communities.Info(item["id"], db) for item in items],
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


# community join
@communities.post("/x{ndcId}/s/community/join")
async def join_community(request: Request, ndcId: int):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession()

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    table = await db.get(table="Communities")
    community = await table.find_one({"ndcId": ndcId})

    if not community:
        await db.close()
        return Errors.CommunityNotFound(timestamp() - t1)

    if trigger_uid in community.get("memberList", []):
        await db.close()
        return Errors.AlreadyJoined(timestamp() - t1)

    await table.update_one(
        {"ndcId": ndcId},
        {
            "$push": {"memberList": trigger_uid},
        },
    )
    await db.close()

    return Base.Answer({}, spent_time=timestamp() - t1)


# community leave
@communities.post("/x{ndcId}/s/community/leave")
async def leave_community(request: Request, ndcId: int):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession()

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    table = await db.get(table="Communities")
    community = await table.find_one({"ndcId": ndcId})

    if not community:
        await db.close()
        return Errors.CommunityNotFound(timestamp() - t1)

    if trigger_uid == community.get("agent") or ndcId == 0:
        await db.close()
        return Errors.NotEnoughRights(timestamp() - t1)

    if trigger_uid not in community.get("memberList", []):
        await db.close()
        return Errors.NotJoined(timestamp() - t1)

    await table.update_one(
        {"ndcId": ndcId},
        {
            "$pull": {"memberList": trigger_uid},
        },
    )

    await db.close()
    return Base.Answer({}, spent_time=timestamp() - t1)
