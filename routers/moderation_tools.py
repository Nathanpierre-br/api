from fastapi import APIRouter, Request
from time import time as timestamp
from objects import Base, Errors
from helpers.database.mongo import Database
from helpers.routers.cachable import CachableRoute

moderation_tools = APIRouter()
moderation_tools.route_class = CachableRoute

ALLOWED_ROLES = [100, 101, 102, 250, 251, 555]


async def check_rights(db, uid: str) -> bool:
    table = await db.get(table="Users")
    user = await table.find_one({"id": uid})
    return user and user.get("role") in ALLOWED_ROLES


@moderation_tools.post("/x{ndcId}/s/user-profile/{uid}/ban")
@moderation_tools.post("/x{ndcId}/s/user-profile/{uid}/unban")
async def ban_user_toggle(uid, request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    db = await Database().init()
    if not await check_rights(db, request.state.session["uid"]):
        await db.close()
        return Errors.NotEnoughRights(spent_time=timestamp() - t1)

    is_unban = "unban" in request.url.path
    status = 0 if is_unban else 9

    table = await db.get(f"x{ndcId}", "Users")
    await table.update_one({"id": uid}, {"$set": {"status": status}})
    await db.close()
    return Base.Answer(spent_time=timestamp() - t1)


async def unban_user(uid, request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    db = await Database().init()
    if not await check_rights(db, request.state.session["uid"]):
        await db.close()
        return Errors.NotEnoughRights(spent_time=timestamp() - t1)

    table = await db.get(f"x{ndcId}", "Users")
    await table.update_one({"id": uid}, {"$set": {"status": 0}})
    await db.close()
    return Base.Answer(spent_time=timestamp() - t1)


@moderation_tools.post("/x{ndcId}/s/{object_type}/{object_id}/hide")
@moderation_tools.post("/x{ndcId}/s/{object_type}/{object_id}/unhide")
async def toggle_hide(ndcId: int, object_type: str, object_id: str, request: Request):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    db = await Database().init()
    if not await check_rights(db, request.state.session["uid"]):
        await db.close()
        return Errors.NotEnoughRights(spent_time=timestamp() - t1)

    is_hide = "hide" in request.url.path
    status = 1 if is_hide else 0

    table_map = {
        "blog": "Blogs",
        "item": "Blogs",
        "chat/thread": "Chats",
        "user-profile": "Users",
    }

    table_name = table_map.get(object_type)
    if not table_name:
        await db.close()
        return Errors.InvalidRequest()

    table = await db.get(f"x{ndcId}", table_name)
    await table.update_one({"id": object_id}, {"$set": {"status": status}})
    await db.close()

    return Base.Answer(spent_time=timestamp() - t1)
