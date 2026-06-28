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

altteam = APIRouter()
altteam.route_class = CachableRoute





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
async def support_reset_password(request: Request, userId: int):
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

        target = await sensitive_table.find_one({"id": userId}, {"communityList": 1})
        if not target:
            return Errors.AccountNotExist(timestamp() - t1)

        community_ids = target.get("communityList", [])

        communities_table = db.get(table="Communities")
        result = []
        async for item in communities_table.find({"id": {"$in": community_ids}}):
            ndc_id = item["id"]
            ndc_users_table = db.get(f"x{ndc_id}", "Users")
            ndc_profile = await ndc_users_table.find_one({"id": userId})
            result.append({
                "id": item.get("id"),
                "aminoId": item.get("aminoId"),
                "name": item.get("name"),
                "icon": item.get("icon"),
                "userProfile": {
                    "nickname": ndc_profile.get("nickname") if ndc_profile else target.get("nickname"),
                    "icon": ndc_profile.get("icon") if ndc_profile else target.get("icon"),
                    "role": ndc_profile.get("role", 0) if ndc_profile else 0,
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