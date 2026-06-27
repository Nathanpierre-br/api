from time import time as timestamp

from fastapi import APIRouter, Request

from helpers.database.mongo import Database
from helpers.decorators.validauth import validauth_required
from helpers.routers.cachable import CachableRoute
from objects import Base, Errors
from objects.types import UserRole

moderation_tools = APIRouter()
moderation_tools.route_class = CachableRoute



async def check_rights(
    db, uid: str, ndcId: int = 0, no_curators: bool = False, only_gods: bool = False
) -> bool:
    table = db.get(f"x{ndcId}", table="Users")
    user = await table.find_one({"id": uid})
    if user is None:
        return False

    role = user.get("role", 0)
    
    if no_curators and role == UserRole.Curator:
        return False

    if only_gods:
        return UserRole.is_global_staff(role)

    return UserRole.is_privileged_role(user.get("role", 0))


# MODERATION HISTORY
# f"/x{self.comId}/s/admin/operation?objectId={userId}&objectType=0&pagingType=t&size={size}",
@moderation_tools.get("/g/s/admin/operation")
@moderation_tools.get("/x{ndcId}/s/admin/operation")
@validauth_required
async def moderation_history(
    request: Request,
    ndcId: int = 0,
    objectId: str = "",
    objectType: int = 0,
    size: int = 25,
):
    """
    example json:
    {
        "author": ,
        "createdTime": ,
        "objectType": ,
        "operationName": ,
        "ndcId": ,
        "referTicketId": ,
        "extData": ,
        "operationDetail": ,
        "operationLevel": ,
        "moderationLevel": ,
        "operation": ,
        "objectId": ,
        "logId": ,
        "objectUrl": ,
    }
    """
    return Base.Answer()


@moderation_tools.post("/g/s/user-profile/{uid}/ban")
@moderation_tools.post("/x{ndcId}/s/user-profile/{uid}/ban")
@moderation_tools.post("/g/s/user-profile/{uid}/unban")
@moderation_tools.post("/x{ndcId}/s/user-profile/{uid}/unban")
@validauth_required
async def ban_user_toggle(request: Request, uid: str, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    db = await Database().init()
    if not await check_rights(db, request.state.session["uid"], ndcId, only_gods=(ndcId == 0)):
        db.close()
        return Errors.NotEnoughRights(spent_time=timestamp() - t1)

    is_unban = "unban" in request.url.path
    status = 0 if is_unban else 9

    table = db.get(f"x{ndcId}", "Users")
    await table.update_one({"id": uid}, {"$set": {"status": status}})
    db.close()
    return Base.Answer(spent_time=timestamp() - t1)


@moderation_tools.post("/x{ndcId}/s/{object_type}/{object_id}/admin")
@moderation_tools.post("/x{ndcId}/s/chat/{object_type}/{object_id}/admin")
@moderation_tools.post("/g/s/{object_type}/{object_id}/admin")
@moderation_tools.post("/g/s/chat/{object_type}/{object_id}/admin")
@validauth_required
async def toggle_hide(
    request: Request, object_type: str, object_id: str, ndcId: int = 0
):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    data = await request.json()

    db = await Database().init()
    if not await check_rights(db, request.state.session["uid"], ndcId, only_gods=(ndcId == 0)):
        db.close()
        return Errors.NotEnoughRights(spent_time=timestamp() - t1)

    table_map = {
        "blog": "Blogs",
        "item": "Blogs",
        "thread": "Chats",
        "chat/thread": "Chats",
        "user-profile": "Users",
    }

    table_name = table_map.get(object_type)
    if not table_name:
        db.close()
        return Errors.InvalidRequest()

    operation = data["adminOpName"]
    value = data.get("adminOpValue")

    if table_name == "Users":
        if operation == 18:
            status = 18
        elif operation == 19:
            status = 0
        else:
            db.close()
            return Errors.UnimplementedPath()

    else:
        if operation == 110:
            if value == 0:
                status = 0
            elif value == 9:
                status = 9
            else:
                db.close()
                return Errors.UnimplementedPath()
        else:
            db.close()
            return Errors.UnimplementedPath()

    table = db.get(f"x{ndcId}", table_name)
    await table.update_one({"id": object_id}, {"$set": {"status": status}})
    db.close()

    return Base.Answer(spent_time=timestamp() - t1)
