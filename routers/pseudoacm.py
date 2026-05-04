from datetime import datetime, UTC
from fastapi import APIRouter, Request
from time import time as timestamp

from objects import Base, Errors
from helpers.database.mongo import Database
from helpers.routers.cachable import CachableRoute
from helpers.decorators.validauth import validauth_required

pseudoacm = APIRouter()
pseudoacm.route_class = CachableRoute


@pseudoacm.post("/x{ndcId}/pacm/community-edit")
@validauth_required
async def edit_community(request: Request, ndcId: int = 0):
    t1 = timestamp()

    trigger_uid = request.state.session["uid"]
    data = await request.json()
    conf = data.get("configuration", {})

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Users")

    user = await table.find_one({"id": trigger_uid})
    if not user or user.get("role", 0) not in [100, 102, 200, 201, 555]:
        await db.close()
        return Errors.NotEnoughRights(timestamp() - t1)

    preparedQueries = {
        "configuration": {},
        "modifiedTime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    for key in [
        "name",
        "aminoId",
        "tagline",
        "description",
        "guidelines",
        "icon",
        "themeUrl",
        "themeColor",
        "themeRevision",
        "coverUrl",
    ]:
        if key in data:
            preparedQueries[key] = data[key]

    for key in ["welcomeMessage", "welcomeMessageEnabled"]:
        if key in conf:
            preparedQueries["configuration"][key] = data[key]

    table = await db.get(table="Communities")
    await table.update_one({"id": ndcId}, {"$set": preparedQueries})

    await db.close()
    return Base.Answer({}, spent_time=timestamp() - t1)
