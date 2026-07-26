from asyncio import to_thread as asyncio_thread

from helpers.aquarium import Blake
from helpers.config import Config
from helpers.database.mongo import Database
from helpers.processors.email import EmailProcessor


from time import time as timestamp

from fastapi import APIRouter, Request

from helpers.routers.cachable import CachableRoute
from objects import Base, Errors
from objects.types import UserRole, UserStatus

from string import ascii_letters, digits
import secrets



from helpers.database.models import Global, ModelFabric
from helpers.generator import Generator
from objects import Links

import uuid
from datetime import UTC, datetime
from objects.types.store import DiscountStatus




def _iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")





altteam = APIRouter()
altteam.route_class = CachableRoute


@altteam.get("/g/s/altteam/version")
async def get_altamino_team(request: Request):
    t1 = timestamp()
    latest_version = "1.0.3"
    current_version = request.query_params.get("version")
    altTeamPage = "https://altamino.top/altapp"
    return Base.Answer(
        {
            "currentVersion": current_version,
            "latestVersion": latest_version,
            "downloadPage": altTeamPage,
        },
        spent_time=timestamp() - t1,
    )

@altteam.get("/g/s/altteam")
async def get_altamino_team(request: Request):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        local_table = db.get(database="x0", table="Users")

        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        global_cursor = sensitive_table.find(
            {"role": {"$in": UserRole.GODS}},
            {"_id": 0, "id": 1, "role": 1, "tagList": 1, "aminoId": 1, "telegramId": 1, "isTeamMember": 1, "isVerified": 1},
        )
        global_members = await global_cursor.to_list(length=None)
        if not global_members:
            return Base.Answer(spent_time=timestamp() - t1, userProfileList=[])

        global_ids = [m["id"] for m in global_members]

        local_cursor = local_table.find(
            {"id": {"$in": global_ids}},
            {
                "_id": 0,
                "id": 1,
                "nickname": 1,
                "icon": 1,
                "reputation": 1,
                "createdTime": 1,
                "modifiedTime": 1,
                "extensions": 1,
            },
        )
        local_profiles = await local_cursor.to_list(length=None)
        local_by_uid = {p["id"]: p for p in local_profiles}
        team_list = []
        for g in global_members:
            profile = local_by_uid.get(g["id"])
            if not profile:
                continue

            merged = dict(profile)
            merged["uid"] = g["id"]
            merged["role"] = g.get("role", 0)
            merged["extensions"]["tagList"] = g.get("tagList", [])
            merged["aminoId"] = g.get("aminoId")
            merged["telegramId"] = g.get("telegramId")
            merged["extensions"]["isMemberOfTeamAmino"] = g.get("isTeamMember", False)
            merged["isNicknameVerified"] = bool(g.get("isVerified", False))
            team_list.append(
                merged   
            )
        return Base.Answer({"userProfileList": team_list}, spent_time=timestamp() - t1)
    finally:
        db.close()


@altteam.get("/g/s/altteam/{userId}")
async def get_altamino_team_member(request: Request, userId: str):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        local_table = db.get(database="x0", table="Users")

        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        global_member = await sensitive_table.find_one(
            {"id": userId, "role": {"$in": UserRole.GODS}},
            {"_id": 0, "id": 1, "role": 1, "tagList": 1, "aminoId": 1, "telegramId": 1, "isTeamMember": 1, "isVerified": 1},
        )
        if not global_member:
            return Errors.InvalidRequest(timestamp() - t1) 

        local_profile = await local_table.find_one(
            {"id": userId},
            {
                "_id": 0,
                "id": 1,
                "nickname": 1,
                "icon": 1,
                "reputation": 1,
                "createdTime": 1,
                "modifiedTime": 1,
                "extensions": 1,
            },
        )
        if not local_profile:
            return Errors.InvalidRequest(timestamp() - t1)

        merged = dict(local_profile)
        merged["uid"] = global_member["id"]
        merged["role"] = global_member.get("role", 0)
        merged["extensions"]["tagList"] = global_member.get("tagList", [])
        merged["aminoId"] = global_member.get("aminoId")
        merged["telegramId"] = global_member.get("telegramId")
        merged["extensions"]["isMemberOfTeamAmino"] = global_member.get("isTeamMember", False)
        merged["isNicknameVerified"] = bool(global_member.get("isVerified", False))

        return Base.Answer({"userProfile": merged}, spent_time=timestamp() - t1)
    except:
        return Errors.InvalidRequest(timestamp() - t1)
    finally:
        db.close()



@altteam.post("/g/s/altteam/telegram/link")
async def link_telegram(request: Request, body: dict):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    telegram_id = body.get("telegramId")
    amino_id = body.get("aminoId")

    if not trigger_uid or telegram_id is None:
        return Errors.InvalidRequest(timestamp() - t1)

    if not isinstance(telegram_id, int):
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or user.get("role", 0) != UserRole.System:
            return Errors.NotEnoughRights(timestamp() - t1)

        target_query = {"aminoId": amino_id} if amino_id else {"id": trigger_uid}

        await sensitive_table.update_one(
            target_query,
            {"$set": {"telegramId": telegram_id}}
        )
        return Base.Answer(spent_time=timestamp() - t1)
    finally:
        db.close()


@altteam.post("/g/s/altteam/telegram/unlink")
async def unlink_telegram(request: Request, body: dict = None):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    
    body = body or {}
    amino_id = body.get("aminoId")

    if not trigger_uid:
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or user.get("role", 0) != UserRole.System:
            return Errors.NotEnoughRights(timestamp() - t1)

        target_query = {"aminoId": amino_id} if amino_id else {"id": trigger_uid}

        await sensitive_table.update_one(
            target_query,
            {"$unset": {"telegramId": ""}}
        )
        return Base.Answer(spent_time=timestamp() - t1)
    finally:
        db.close()






@altteam.post("/g/s/altteam/{userId}/edit")
async def edit_altteam_member(request: Request, userId: str, body: dict):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")

    if not trigger_uid:
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        
        trigger_user = await sensitive_table.find_one({"id": trigger_uid})
        if not trigger_user or trigger_user.get("role", 0) != UserRole.AltAminoStaff:
            return Errors.NotEnoughRights(timestamp() - t1)
        
        target_user = await sensitive_table.find_one({"id": userId})
        if not target_user:
            return Errors.InvalidRequest(timestamp() - t1)
        
        update_fields = {}
        
        new_role = body.get("role")
        is_verified = body.get("isVerified")
        new_tags = body.get("tagList")
        altteam_status = body.get("isMemberOfTeamAmino")
        
        if new_role is not None:
            if target_user.get("role", 0) == UserRole.AltAminoStaff or userId == trigger_uid:
                return Errors.NotEnoughRights(timestamp() - t1)
            if not UserRole.is_valid_role(new_role):
                return Errors.InvalidRequest(timestamp() - t1)
            
            update_fields["role"] = new_role
            
        if new_tags is not None:
            if isinstance(new_tags, list):
                update_fields["tagList"] = new_tags

        if altteam_status is not None:
            update_fields["isTeamMember"] = altteam_status

        if is_verified is not None:
            update_fields["isVerified"] = is_verified

        if update_fields:
            await sensitive_table.update_one({"id": userId}, {"$set": update_fields})
        
        return Base.Answer(spent_time=timestamp() - t1)
    except:
        return Errors.InvalidRequest(timestamp() - t1)
    finally:
        db.close()





@altteam.post("/g/s/altteam/reset-password")
async def support_reset_password(request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not Config.ENABLE_EMAIL:
        return Errors.PathUnderMaintenance(timestamp() - t1)
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    sensitive_table = db.get(table="Users")
    user = await sensitive_table.find_one({"id": trigger_uid})
    if not user or not UserRole.is_global_staff(user.get("role", 0)):
        db.close()
        return Errors.NotEnoughRights(timestamp() - t1)
    try:
        secret = ''.join(secrets.choice(ascii_letters + digits) for _ in range(12))
        data = await request.json()
        updateSecret = Blake(
            data=f"0 {secret}",
            key=Config.PASSWORD_SALT,
            digest_size=64,
        ).hash
        email = data["email"]
    except Exception:
        return Errors.InvalidRequest(timestamp() - t1)
    if not await EmailProcessor.Validate(email):
        return Errors.InvalidEmail(timestamp() - t1)
    table = db.get(table="Users")
    await table.update_one({"email": email}, {"$set": {"passwordHash": updateSecret}})
    db.close()

    html = """<h3>Your AltAmino password has been reset by support.</h3><p>Your new password is:</p><h2>{{ PASSWORD }}</h2><p>Please log in using this password and change it as soon as possible in your account settings.</p><p>If you did not request this, please contact us immediately.</p><br><p>Thanks,<br>Team AltAmino</p>"""
    text = "Your AltAmino password has been reset by support. Your new temporary password is: {{ PASSWORD }}. Please log in and change it as soon as possible in your account settings. If you did not request this, please contact us immediately."

    html = html.replace("{{ PASSWORD }}", secret)
    text = text.replace("{{ PASSWORD }}", secret)
    subject = "Your AltAmino password has been reset"

    try:
        await asyncio_thread(
            EmailProcessor.SendEmail,
            receiver=email,
            subject=subject,
            html=html,
            text=text,
        )
    except Exception as e:
        print(e)
        return Errors.MailError(timestamp() - t1)
    return Base.Answer(
        {},
        spent_time=timestamp() - t1,
    )




@altteam.post("/g/s/altteam/user-profile/{userId}/status")
async def set_user_status(request: Request, userId: str):
    t1 = timestamp()
    if not Config.ENABLE_EMAIL:
        return Errors.PathUnderMaintenance(timestamp() - t1)
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    sensitive_table = db.get(table="Users")
    user = await sensitive_table.find_one({"id": trigger_uid})
    if not user or not UserRole.is_global_staff(user.get("role", 0)):
        db.close()
        return Errors.NotEnoughRights(timestamp() - t1)
    try:
        data = await request.json()
        status = data.get("status", 0)
        if not UserStatus.is_valid_status(status):
            raise Exception
    except Exception:
        return Errors.InvalidRequest(timestamp() - t1)
    
    table = db.get(table="Users")
    await table.update_one({"id": userId}, {"$set": {"status": status}})
    db.close()
    
    return Base.Answer(
        {},
        spent_time=timestamp() - t1,
    )



@altteam.get("/g/s/altteam/user-profile/{userId}/communities")
async def get_user_communities(request: Request, userId: str):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        target = await sensitive_table.find_one({"id": userId}, {"communityList": 1, "nickname": 1, "icon": 1})
        if not target:
            return Errors.AccountNotExist(timestamp() - t1)

        community_ids = target.get("communityList", [])

        communities_table = db.get(table="Communities")
        links_table = db.get(table="Links")
        result = []
        
        async for item in communities_table.find({"id": {"$in": community_ids}}):
            ndc_id = item["id"]
            ndc_users_table = db.get(f"x{ndc_id}", "Users")
            ndc_profile = await ndc_users_table.find_one({"id": userId})
            
            link = await links_table.find_one(
                {"objectId": userId, "objectType": 0, "ndcId": int(ndc_id)}
            )
            
            if link is None and ndc_profile:
                link = ModelFabric.Construct(
                    Global.Links,
                    code=Generator.RealString(8),
                    targetCode=1,
                    objectId=userId,
                    objectType=0,
                    ndcId=int(ndc_id),
                )
                await links_table.insert_one(link)


            if link:
                link_data = Links.User(link)
            else:
                link_data = None

            result.append({
                "ndcId": item.get("id"),
                "endpoint": item.get("aminoId"),
                "name": item.get("name"),
                "icon": item.get("icon"),
                "userProfile": {
                    "nickname": ndc_profile.get("nickname") if ndc_profile else target.get("nickname"),
                    "icon": ndc_profile.get("icon") if ndc_profile else target.get("icon"),
                    "role": ndc_profile.get("role", 0) if ndc_profile else 0,
                    "linkData": link_data
                }
            })

        return Base.Answer(
            {
                "communityList": result,
                "communityCount": len(result),
            },
            spent_time=timestamp() - t1,
        )
    finally:
        db.close()







#STORE




#  Avatar Frames

@altteam.post("/g/s/altteam/altstore/avatar-frame")
async def create_frame(request: Request):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        try:
            data = await request.json()
            name = data["name"]
            resource_url = data["resourceUrl"]
        except Exception:
            return Errors.InvalidRequest(timestamp() - t1)

        frame_id = str(uuid.uuid4())
        doc = {
            "frameId": frame_id,
            "name": name,
            "resourceUrl": resource_url,
            "icon": data.get("icon"),
            "frameType": data.get("frameType", 1),
            "description": data.get("description", ""),
            "price": data.get("price", 0),
            "restrictType": data.get("restrictType"),
            "discountStatus": data.get("discountStatus", DiscountStatus.OFF),
            "discountValue": data.get("discountValue", 0),
            "availableDuration": data.get("availableDuration", 0),
            "md5": data.get("md5"),
            "version": data.get("version", 1),
            "status": 0,
            "uid": trigger_uid,
            "createdTime": _iso(),
            "modifiedTime": _iso(),
            "extensions": {},
        }

        frames = db.get(table="AvatarFrames")
        await frames.insert_one(doc)
        doc.pop("_id", None)

        return Base.Answer({"frameId": frame_id, "avatarFrame": doc}, spent_time=timestamp() - t1)
    finally:
        db.close()


@altteam.post("/g/s/altteam/altstore/avatar-frame/{frameId}/edit")
async def edit_frame(request: Request, frameId: str):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        try:
            data = await request.json()
        except Exception:
            return Errors.InvalidRequest(timestamp() - t1)

        allowed = {
            "name", "resourceUrl", "icon", "frameType", "description",
            "price", "restrictType", "discountStatus", "discountValue",
            "availableDuration", "md5", "version", "status",
        }
        changes = {k: v for k, v in data.items() if k in allowed and v is not None}
        if not changes:
            return Errors.InvalidRequest(timestamp() - t1)
        changes["modifiedTime"] = _iso()

        frames = db.get(table="AvatarFrames")
        result = await frames.update_one({"frameId": frameId}, {"$set": changes})
        if result.matched_count == 0:
            return Errors.InvalidRequest(timestamp() - t1)

        return Base.Answer(spent_time=timestamp() - t1)
    finally:
        db.close()


@altteam.post("/g/s/altteam/altstore/avatar-frame/{frameId}/delete")
async def delete_frame(request: Request, frameId: str):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        frames = db.get(table="AvatarFrames")
        result = await frames.delete_one({"frameId": frameId})
        if result.deleted_count == 0:
            return Errors.InvalidRequest(timestamp() - t1)

        return Base.Answer(spent_time=timestamp() - t1)
    finally:
        db.close()


@altteam.get("/g/s/altteam/altstore/avatar-frame")
async def list_frames(request: Request):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        frames = db.get(table="AvatarFrames")
        docs = await frames.find({}, {"_id": 0}).to_list(length=None)

        return Base.Answer({"avatarFrameList": docs}, spent_time=timestamp() - t1)
    finally:
        db.close()



#  Chat Bubbles


@altteam.post("/g/s/altteam/altstore/chat-bubble")
async def create_bubble(request: Request):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        try:
            data = await request.json()
            name = data["name"]
            resource_url = data["resourceUrl"]
        except Exception:
            return Errors.InvalidRequest(timestamp() - t1)

        bubble_id = str(uuid.uuid4())
        doc = {
            "bubbleId": bubble_id,
            "name": name,
            "resourceUrl": resource_url,
            "coverImage": data.get("coverImage"),
            "backgroundImage": data.get("backgroundImage"),
            "bannerImage": data.get("bannerImage"),
            "bubbleType": data.get("bubbleType", 1),
            "config": data.get("config", {}),
            "templateId": data.get("templateId"),
            "price": data.get("price", 0),
            "restrictType": data.get("restrictType"),
            "discountStatus": data.get("discountStatus", DiscountStatus.OFF),
            "discountValue": data.get("discountValue", 0),
            "availableDuration": data.get("availableDuration", 0),
            "md5": data.get("md5"),
            "version": data.get("version", 1),
            "status": 0,
            "deletable": True,
            "uid": trigger_uid,
            "createdTime": _iso(),
            "modifiedTime": _iso(),
            "extensions": {},
        }

        bubbles = db.get(table="ChatBubbles")
        await bubbles.insert_one(doc)
        doc.pop("_id", None)

        return Base.Answer({"bubbleId": bubble_id, "chatBubble": doc}, spent_time=timestamp() - t1)
    finally:
        db.close()


@altteam.post("/g/s/altteam/altstore/chat-bubble/{bubbleId}/edit")
async def edit_bubble(request: Request, bubbleId: str):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        try:
            data = await request.json()
        except Exception:
            return Errors.InvalidRequest(timestamp() - t1)

        allowed = {
            "name", "resourceUrl", "coverImage", "backgroundImage", "bannerImage",
            "bubbleType", "config", "templateId", "price", "restrictType",
            "discountStatus", "discountValue", "availableDuration", "md5",
            "version", "status", "deletable",
        }
        changes = {k: v for k, v in data.items() if k in allowed and v is not None}
        if not changes:
            return Errors.InvalidRequest(timestamp() - t1)
        changes["modifiedTime"] = _iso()

        bubbles = db.get(table="ChatBubbles")
        result = await bubbles.update_one({"bubbleId": bubbleId}, {"$set": changes})
        if result.matched_count == 0:
            return Errors.InvalidRequest(timestamp() - t1)

        return Base.Answer(spent_time=timestamp() - t1)
    finally:
        db.close()


@altteam.post("/g/s/altteam/altstore/chat-bubble/{bubbleId}/delete")
async def delete_bubble(request: Request, bubbleId: str):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        bubbles = db.get(table="ChatBubbles")
        result = await bubbles.delete_one({"bubbleId": bubbleId})
        if result.deleted_count == 0:
            return Errors.InvalidRequest(timestamp() - t1)

        return Base.Answer(spent_time=timestamp() - t1)
    finally:
        db.close()


@altteam.get("/g/s/altteam/altstore/chat-bubble")
async def list_bubbles(request: Request):
    t1 = timestamp()
    trigger_uid = request.state.session.get("uid")
    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            return Errors.NotEnoughRights(timestamp() - t1)

        bubbles = db.get(table="ChatBubbles")
        docs = await bubbles.find({}, {"_id": 0}).to_list(length=None)

        return Base.Answer({"chatBubbleList": docs}, spent_time=timestamp() - t1)
    finally:
        db.close()