from time import time as timestamp

from fastapi import APIRouter, Request

from helpers.database.mongo import Database
from helpers.decorators.validauth import validauth_required
from helpers.routers.cachable import CachableRoute
from objects import Base, Errors
from objects.types import UserRole
from datetime import datetime
from uuid import uuid4

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
    table = db.get(f"x{ndcId}", table_name)

    if table_name == "Users":
        if operation == 18:
            await table.update_one(
                {"id": object_id},
                {"$set": {
                    "status": 9,
                    "extensions.__disabledLevel__": 3
                }}
            )
        elif operation == 19:
            await table.update_one(
                {"id": object_id},
                {"$set": {
                    "status": 0,
                    "extensions.__disabledLevel__": 0
                }}
            )
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

        await table.update_one({"id": object_id}, {"$set": {"status": status}})

    db.close()
    return Base.Answer(spent_time=timestamp() - t1)





@moderation_tools.post("/x{ndcId}/s/notice")
@moderation_tools.post("/g/s/notice")
@validauth_required
async def send_notice(request: Request, ndcId: int = 0):
    t1 = timestamp()
    uid = request.state.session["uid"]
    data = await request.json()

    db = await Database().init()
    if not await check_rights(db, uid, ndcId, only_gods=(ndcId == 0)):
        db.close()
        return Errors.NotEnoughRights(spent_time=timestamp() - t1)

    try:
        target_uid = data["uid"]
        title = data["title"]
        content = data["content"]
        penalty_type = data.get("penaltyType", 0)   # 0 = warning, 1 = strike
        penalty_value = data.get("penaltyValue", 0)  # seconds for strike
        notice_type = data.get("noticeType", 7)      # 4 = strike, 7 = warning
        attached_object = data.get("attachedObject", {})
    except KeyError:
        db.close()
        return Errors.InvalidRequest(timestamp() - t1)

    notice = {
        "id": str(uuid4()),
        "uid": target_uid,
        "triggerId": uid,
        "title": title,
        "content": content,
        "attachedObject": attached_object,
        "penaltyType": penalty_type,
        "penaltyValue": penalty_value,
        "noticeType": notice_type,
        "ndcId": ndcId,
        "createdTime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    table = db.get(f"x{ndcId}", "Notices")
    await table.insert_one(notice)

    if penalty_type == 1 and penalty_value > 0:
        # TODO: make temp ban 
        pass

    db.close()
    return Base.Answer({}, spent_time=timestamp() - t1)


@moderation_tools.get("/x{ndcId}/s/notice/message-template/{template_type}")
@moderation_tools.get("/g/s/notice/message-template/{template_type}")
async def get_notice_templates(request: Request, template_type: str, ndcId: int = 0):
    t1 = timestamp()
    #can be anything i think, it's just template
    STRIKE_TEMPLATES = [
        {"id": "strike-1", "title": "Spam", "content": "Your content was removed for spam. Please follow community guidelines.", "messageType": 4},
        {"id": "strike-2", "title": "Inappropriate content", "content": "Your content was removed for violating our community rules regarding inappropriate content.", "messageType": 4},
        {"id": "strike-3", "title": "Harassment", "content": "Your content was removed for harassment or bullying of other members.", "messageType": 4},
        {"id": "strike-4", "title": "NSFW content", "content": "Your content was removed for containing NSFW or adult material which is not allowed on this platform.", "messageType": 4},
        {"id": "strike-5", "title": "Misinformation", "content": "Your content was removed for spreading misinformation or false information.", "messageType": 4},
    ]

    WARNING_TEMPLATES = [
        {"id": "warn-1", "title": "Friendly reminder", "content": "This is a friendly reminder to please follow our community guidelines.", "messageType": 7},
        {"id": "warn-2", "title": "Spam warning", "content": "Please avoid posting repetitive or promotional content in this community.", "messageType": 7},
        {"id": "warn-3", "title": "Behavior warning", "content": "Your recent behavior was not in line with our community standards. Please be respectful to other members.", "messageType": 7},
        {"id": "warn-4", "title": "Content warning", "content": "Please make sure your content follows our community rules before posting.", "messageType": 7},
    ]

    if template_type == "strike":
        templates = STRIKE_TEMPLATES
    elif template_type == "warning":
        templates = WARNING_TEMPLATES
    else:
        return Errors.InvalidRequest(timestamp() - t1)

    return Base.Answer(
        {"messageTemplateList": templates},
        spent_time=timestamp() - t1,
    )