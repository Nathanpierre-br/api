from datetime import UTC, datetime
from time import time as timestamp

from fastapi import APIRouter, Request

from helpers.config import Config
from helpers.database.mongo import Database
from helpers.decorators.validauth import validauth_required
from helpers.routers.cachable import CachableRoute
from objects import Base, Errors

altacm = APIRouter()
altacm.route_class = CachableRoute

WHO_HAVE_POWER_OF_GOD = [200, 201, 254, 555]


@altacm.post("/altacm/s/community/x{ndcId}/user/{userId}/promote")
@altacm.delete("/altacm/s/community/x{ndcId}/user/{userId}/promote")
@validauth_required
async def promotions(request: Request, ndcId: int, userId: str):
    t1 = timestamp()

    trigger_uid = request.state.session["uid"]
    destruction_mode = request.method == "DELETE"
    data = await request.json()
    role = data.get("role")
    if not destruction_mode and (role is None or not role.isdigit()):
        return Errors.InvalidRequest()

    db = await Database().init()
    sensitive_table = db.get(table="Users")
    ndc_users_table = db.get(f"x{ndcId}", "Users")

    user = await sensitive_table.find_one({"id": trigger_uid})
    if not user or user.get("role", 0) not in WHO_HAVE_POWER_OF_GOD:
        db.close()
        return Errors.NotEnoughRights(timestamp() - t1)

    if destruction_mode:
        role = 0
    else:
        role = int(role)
        if role < 100 or role > 102:
            return Errors.InvalidRequest()

    await ndc_users_table.update_one({"id": userId}, {"$set": {"role": role}})

    return Base.Answer(spent_time=timestamp() - t1)


@altacm.post("/altacm/s/community/create")
@validauth_required
async def create_community(request: Request):
    t1 = timestamp()

    trigger_uid = request.state.session["uid"]
    data = await request.json()

    # ok, did we got everything we need?
    fields = ["name", "aminoId", "agentGlobalLink", "lang"]
    missing_fields = [field for field in fields if field not in data]
    if missing_fields:
        return Errors.InvalidRequest(timestamp() - t1)

    # it should be a global link since its easier and logical
    if f"{Config.SITE_DOMAIN}/u/" not in data["agentGlobalLink"]:
        return Errors.InvalidRequest(timestamp() - t1)
    agentAminoId = data["agentGlobalLink"].split("/")[-1]

    # do you have rights to create a community?
    db = await Database().init()
    sensitive_table = db.get(table="Users")

    user = await sensitive_table.find_one({"id": trigger_uid})
    if not user or user.get("role", 0) not in WHO_HAVE_POWER_OF_GOD:
        db.close()
        return Errors.NotEnoughRights(timestamp() - t1)

    # cool! lets begin from grabbing the latest community id
    ndclist_table = db.get(table="Communities")
    latest_community = await ndclist_table.find_one(sort=[("id", -1)])
    if latest_community and latest_community.get("id"):
        ndcId = latest_community["id"] + 1  # new one for new community!
    else:
        ndcId = 1  # oh, we can meet our first community then!

    # and grab global community as a starting point of shaping new community
    shape = await ndclist_table.find_one({"id": 0})
    if not shape:
        # and if it not exist... bruh.
        return Errors.InternalServerError(timestamp() - t1)

    # now we are resetting some fields to make sure the new community starts fresh and clean
    shape["id"] = ndcId
    shape["name"] = data["name"]
    shape["aminoId"] = data["aminoId"]
    shape["lang"] = data["lang"] if data["lang"] in ["en", "ru", "es", "ar"] else "en"
    for key in ["_id", "theme"]:  # [NOTE] theme is old key that is not used
        shape.pop(key, None)

    # but what about members?
    # there should be TA account, Astral (if exist) and an agent themselves!
    aminoIds = ["teamaltamino", "astral", agentAminoId]
    global_table = db.get("x0", "Users")
    new_users_table = db.get(f"x{ndcId}", "Users")
    who_joined = []
    for aminoId in aminoIds:
        aid2id_request = await sensitive_table.find_one(
            {"aminoId": aminoId}, projection={"id": 1, "_id": 0}
        )

        # account should exist (except astral, he is not that important)
        if not aid2id_request and aminoId != "astral":
            return Errors.InternalServerError(timestamp() - t1)

        # getting account info from global aka x0
        uid = aid2id_request["id"]
        profile = await global_table.find_one({"id": uid})
        if not profile:
            return Errors.InternalServerError(timestamp() - t1)

        # and cleaning it for new community
        modtime = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        profile.pop("_id", None)
        profile["wall"] = {}
        profile["whoFollows"] = []
        profile["following"] = []
        profile["titles"] = []
        profile["savedBlogs"] = []
        profile["consecutiveDaysOfCheckIns"] = 0
        profile["reputation"] = 0
        profile["minutesPerDay"] = 0
        profile["minutesPerWeek"] = 0
        profile["createdTime"] = modtime
        profile["modifiedTime"] = modtime
        if aminoId == agentAminoId:
            shape["agent"] = uid
            profile["role"] = 102

        # and inserting this into the database
        await new_users_table.insert_one(profile)

        who_joined.append(uid)

    # did you forgot about adding the community to the database?
    # not really. we at first need to add users, because of some fields
    shape["memberList"] = who_joined
    shape["membersCount"] = len(who_joined)
    await ndclist_table.insert_one(shape)

    # and now we need to update sensetive user infos
    # to properly show that community is created and they are members of it
    await sensitive_table.update_many(
        {"id": {"$in": who_joined}},
        {"$addToSet": {"communityList": ndcId}},
    )

    # hooray! we are done
    db.close()
    return Base.Answer(spent_time=timestamp() - t1)


@altacm.delete("/altacm/s/community/x{ndcId}/destroy")
@validauth_required
async def destroy_community(request: Request, ndcId: int):
    t1 = timestamp()

    # how you dare destroying community!
    #
    # btw it can helps if there is some
    # malicious community going around
    # that can hurt us in any ways

    trigger_uid = request.state.session["uid"]

    # do you even have rights to do this act?
    db = Database()
    sensitive_table = db.get(table="Users")

    user = await sensitive_table.find_one({"id": trigger_uid})
    if not user or user.get("role", 0) not in WHO_HAVE_POWER_OF_GOD:
        db.close()
        return Errors.NotEnoughRights(timestamp() - t1)

    # well.. fine. we will delete everything
    # starting from communities table
    ndclist_table = db.get(table="Communities")
    await ndclist_table.delete_one({"id": ndcId})

    # now we can nuke community database
    await db.connection.drop_database(f"x{ndcId}")

    # but what about who joined community?
    condition = {"communityList": ndcId}
    await sensitive_table.update_many(condition, {"$pull": condition})

    # *sigh*... we are done.
    db.close()
    return Base.Answer(spent_time=timestamp() - t1)


@altacm.post("/altacm/s/community/x{ndcId}/edit")
@validauth_required
async def edit_community(request: Request, ndcId: int = 0):
    t1 = timestamp()

    trigger_uid = request.state.session["uid"]
    data = await request.json()
    conf = data.get("configuration", {})

    db = await Database().init()
    table = db.get(f"x{ndcId}", "Users")

    user = await table.find_one({"id": trigger_uid})
    if not user or user.get("role", 0) not in WHO_HAVE_POWER_OF_GOD:
        db.close()
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

    table = db.get(table="Communities")
    await table.update_one({"id": ndcId}, {"$set": preparedQueries})

    db.close()
    return Base.Answer({}, spent_time=timestamp() - t1)
