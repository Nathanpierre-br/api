from datetime import UTC, datetime
from time import time as timestamp

from fastapi import APIRouter, Request

from helpers.config import Config
from helpers.database.mongo import Database
from helpers.decorators.validauth import validauth_required
from helpers.routers.cachable import CachableRoute
from objects import Base, Errors, Communities
from objects.types import UserRole

altacm = APIRouter()
altacm.route_class = CachableRoute


@altacm.post("/altacm/s/community/x{ndcId}/user/{userId}/promote")
@altacm.delete("/altacm/s/community/x{ndcId}/user/{userId}/promote")
@validauth_required
async def promotions(request: Request, ndcId: int, userId: str):
    t1 = timestamp()

    trigger_uid = request.state.session["uid"]
    destruction_mode = request.method == "DELETE"

    if not destruction_mode:
        data = await request.json()
        role = data.get("role")
        if not isinstance(role, int) or not UserRole.is_local_staff(role):
            return Errors.InvalidRequest(timestamp() - t1)
    else:
        role = UserRole.User

    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")
        communities_table = db.get(table="Communities")
        ndc_users_table = db.get(f"x{ndcId}", table="Users")

        user = await sensitive_table.find_one({"id": trigger_uid})
        local_user = await ndc_users_table.find_one({"id": trigger_uid})
        gu = await ndc_users_table.find_one({"id": userId})

        if not gu:
            return Errors.InvalidRequest(timestamp() - t1)

        is_god = bool(user) and UserRole.is_global_staff(user.get("role", 0))
        is_admin = bool(local_user) and UserRole.is_local_admin(
            local_user.get("role", 0)
        )

        if not (is_god or is_admin):
            return Errors.NotEnoughRights(timestamp() - t1)

        if role == UserRole.Agent:
            trigger_is_agent = (
                bool(local_user) and local_user.get("role", 0) == UserRole.Agent
            )
            if not (is_god or trigger_is_agent):
                return Errors.NotEnoughRights(timestamp() - t1)

            old_agent = await ndc_users_table.find_one({"role": UserRole.Agent})
            if old_agent and old_agent["id"] != userId:
                await ndc_users_table.update_one(
                    {"id": old_agent["id"]}, {"$set": {"role": UserRole.Leader}}
                )
            await communities_table.update_one(
                {"id": ndcId}, {"$set": {"agent": userId}}
            )

        await ndc_users_table.update_one({"id": userId}, {"$set": {"role": role}})

        return Base.Answer(spent_time=timestamp() - t1)

    finally:
        db.close()


@altacm.post("/altacm/s/community/create")
@validauth_required
async def create_community(request: Request):
    t1 = timestamp()

    trigger_uid = request.state.session["uid"]
    data = await request.json()

    fields = ["name", "aminoId", "lang"]
    missing_fields = [field for field in fields if field not in data]
    if missing_fields:
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()
    try:
        sensitive_table = db.get(table="Users")

        user = await sensitive_table.find_one({"id": trigger_uid})
        if not user or not UserRole.is_global_staff(user.get("role", 0)):
            # For now, we will prohibit the creation of communities by users themselves.
            db.close()
            return Errors.NotEnoughRights(timestamp() - t1)

        ndclist_table = db.get(table="Communities")

        existing_community = await ndclist_table.find_one({"aminoId": data["aminoId"]})
        if existing_community:
            db.close()
            return Errors.Exs9(timestamp() - t1)

        is_staff = UserRole.is_global_staff(user.get("role", 0))
        agentAminoId = None

        if "agentGlobalLink" in data and data["agentGlobalLink"]:
            if not is_staff:
                db.close()
                return Errors.NotEnoughRights(timestamp() - t1)

            if f"{Config.SITE_DOMAIN}/u/" not in data["agentGlobalLink"]:
                db.close()
                return Errors.InvalidRequest(timestamp() - t1)

            agentAminoId = data["agentGlobalLink"].split("/")[-1]
        else:
            agentAminoId = user.get("aminoId")
            if not agentAminoId:
                db.close()
                return Errors.InternalServerError(timestamp() - t1)

        latest_community = await ndclist_table.find_one(sort=[("id", -1)])
        if latest_community and latest_community.get("id"):
            ndcId = latest_community["id"] + 1
        else:
            ndcId = 1

        shape = await ndclist_table.find_one({"id": 0})
        if not shape:
            db.close()
            return Errors.InternalServerError(timestamp() - t1)

        shape["id"] = ndcId
        shape["name"] = data["name"]
        shape["aminoId"] = data["aminoId"]
        shape["hidden"] = False
        shape["lang"] = (
            data["lang"] if data["lang"] in ["en", "ru", "es", "ar"] else "en"
        )
        for key in ["_id", "theme"]:
            shape.pop(key, None)

        aminoIds = ["teamaltamino", "astral", agentAminoId]
        global_table = db.get("x0", "Users")
        new_users_table = db.get(f"x{ndcId}", "Users")
        who_joined = []

        for aminoId in aminoIds:
            aid2id_request = await sensitive_table.find_one(
                {"aminoId": aminoId}, projection={"id": 1, "_id": 0}
            )

            if not aid2id_request and aminoId != "astral":
                db.close()
                return Errors.InternalServerError(timestamp() - t1)

            if not aid2id_request and aminoId == "astral":
                continue

            uid = aid2id_request["id"]

            if uid in who_joined:
                continue

            profile = await global_table.find_one({"id": uid})
            if not profile:
                db.close()
                return Errors.InternalServerError(timestamp() - t1)

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

            await new_users_table.insert_one(profile)
            who_joined.append(uid)

        shape["memberList"] = who_joined
        shape["membersCount"] = len(who_joined)
        await ndclist_table.insert_one(shape)

        await sensitive_table.update_many(
            {"id": {"$in": who_joined}},
            {"$addToSet": {"communityList": ndcId}},
        )

        return Base.Answer(
            {
                "community": {
                    "ndcId": shape["id"],
                    "name": shape["name"],
                    "aminoId": shape["aminoId"],
                    "lang": shape["lang"],
                    "membersCount": shape["membersCount"],
                    "icon": shape.get("icon"),
                }
            },
            spent_time=timestamp() - t1,
        )
    finally:
        db.close()


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
    ndc_users_table = db.get(f"x{ndcId}", table="Users")

    user = await sensitive_table.find_one({"id": trigger_uid})
    local_user = await ndc_users_table.find_one({"id": trigger_uid})

    is_god = bool(user) and UserRole.is_global_staff(user.get("role", 0))
    is_agent = bool(local_user) and local_user.get("role", 0) == UserRole.Agent

    if not (is_god or is_agent):
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

    # *sigh*... we are done.    // bro wtf??? -_-
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
    try:
        global_users_table = db.get(table="Users")
        global_user = await global_users_table.find_one({"id": trigger_uid})

        is_global = global_user and UserRole.is_global_staff(global_user.get("role", 0))
        is_allowed = is_global

        if not is_allowed:
            local_users_table = db.get(f"x{ndcId}", "Users")
            local_user = await local_users_table.find_one({"id": trigger_uid})

            if local_user and local_user.get("role", 0) in (
                UserRole.Leader,
                UserRole.Agent,
            ):
                is_allowed = True

        if not is_allowed:
            return Errors.NotEnoughRights(timestamp() - t1)

        preparedQueries = {
            "modifiedTime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        for key in [
            "name",
            "aminoId",
            "tagline",
            "description",
            "guideline",
            "guidelineMediaList",
            "mediaList",
            "icon",
            "themeUrl",
            "themeColor",
            "themeRevision",
            "coverUrl",
        ]:
            if key in data:
                preparedQueries[key] = data[key]

        if is_global:
            if "lang" in data:
                lang_val = data["lang"]
                preparedQueries["lang"] = (
                    lang_val if lang_val in ["en", "ru", "es", "ar"] else "en"
                )

            try:
                if "joinType" in conf:
                    preparedQueries["joinType"] = (
                        int(conf["joinType"]) if conf["joinType"] in [0, 1, 2] else 0
                    )
                if "hidden" in conf:
                    preparedQueries["hidden"] = bool(conf["hidden"])
            except Exception:
                return Errors.InvalidRequest(timestamp() - t1)

        for key in ["welcomeMessage", "welcomeMessageEnabled"]:
            if key in conf:
                preparedQueries[f"configuration.{key}"] = conf[key]

        communities_table = db.get(table="Communities")

        if "aminoId" in preparedQueries:
            existing_community = await communities_table.find_one(
                {"aminoId": preparedQueries["aminoId"], "id": {"$ne": ndcId}}
            )
            if existing_community:
                return Errors.Exs9(timestamp() - t1)

        await communities_table.update_one({"id": ndcId}, {"$set": preparedQueries})

        return Base.Answer({}, spent_time=timestamp() - t1)

    finally:
        db.close()

@altacm.post("/altacm/s/community/x{ndcId}/theme-pack")
@validauth_required
async def get_community_themePack(request: Request, ndcId: int = 0):
    t1 = timestamp()

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    try:
        global_users_table = db.get(table="Users")
        global_user = await global_users_table.find_one({"id": trigger_uid})

        is_global = global_user and UserRole.is_global_staff(global_user.get("role", 0))
        is_allowed = is_global

        if not is_allowed:
            local_users_table = db.get(f"x{ndcId}", "Users")
            local_user = await local_users_table.find_one({"id": trigger_uid})

            if local_user and local_user.get("role", 0) in (
                UserRole.Leader,
                UserRole.Agent,
            ):
                is_allowed = True

        if not is_allowed:
            return Errors.NotEnoughRights(timestamp() - t1)

        communities_table = db.get(table="Communities")
        theme = await communities_table.find_one(
            {"id": ndcId},
            projection={"themeUrl": 1, "themeRevision": 1, "themeColor": 1, "_id": 0},
        )
        return Base.Answer(
            {
                "themeUrl": theme.get("themeUrl"),
                "themeRevision": theme.get("themeRevision"),
                "themeColor": theme.get("themeColor"),
            },
            spent_time=timestamp() - t1,
        )

    finally:
        db.close()


@altacm.get("/altacm/s/user-profile/{userId}/moderated-communities")
@validauth_required
async def communities_with_role(request: Request, userId: str):
    t1 = timestamp()
    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    try:
        users = db.get(table="Users")

        trigger_user = await users.find_one({"id": trigger_uid})
        if not trigger_user or (
            trigger_uid != userId
            and not UserRole.is_global_staff(trigger_user.get("role", 0))
        ):
            return Errors.NotEnoughRights(timestamp() - t1)

        target_user = await users.find_one(
            {"id": userId},
            projection={"communityList": 1, "_id": 0},
        )
        if not target_user:
            return Errors.AccountNotExist(timestamp() - t1)

        community_ids = [i for i in target_user.get("communityList", []) if i]

        matching_ndc_ids = []
        for ndcId in community_ids:
            community_users = db.get(database=f"x{ndcId}", table="Users")

            member = await community_users.find_one(
                {"id": userId},
                projection={"role": 1, "_id": 0},
            )

            if member and member.get("role") in (UserRole.Leader, UserRole.Agent):
                matching_ndc_ids.append(ndcId)

        return Base.Answer(
            {"communityIdList": matching_ndc_ids},
            spent_time=timestamp() - t1,
        )
    finally:
        db.close()









async def _can_edit_community(db, ndcId: int, trigger_uid: str) -> bool:
    global_user = await db.get(table="Users").find_one({"id": trigger_uid})
    if global_user and UserRole.is_global_staff(global_user.get("role", 0)):
        return True
    local_user = await db.get(f"x{ndcId}", "Users").find_one({"id": trigger_uid})
    return bool(local_user) and local_user.get("role", 0) in (
        UserRole.Leader,
        UserRole.Agent,
    )





MODULE_SCHEMA = {
    "post": {
        "enabled": (bool, True),
        "blog":     ("module_info", None),
        "poll":     ("module_info", None),
        "image":    ("module_info", None),
        "question": ("module_info", None),
    },
    "chat": {
        "enabled": (bool, True),
        "spamProtectionEnabled": (bool, True),
        "publicChat": ("module_info", None),
        "avChat.screeningRoomEnabled": (bool, False),
        "avChat.audioEnabled": (bool, True),
        "avChat.videoEnabled": (bool, False),
        "avChat.audio2Enabled": (bool, True),
    },
    "ranking": {
        "enabled": (bool, True),
        "leaderboardEnabled": (bool, False),
    },
    "featured": {
        "enabled": (bool, False),
        "postEnabled": (bool, False),
        "memberEnabled": (bool, False),
        "publicChatRoomEnabled": (bool, False),
        "layout": (int, 1),
    },
    "catalog": {
        "enabled": (bool, False),
        "curationEnabled": (bool, False),
    },
    "sharedFolder": {
        "enabled": (bool, False),
        "uploadPrivilege": (int, 2),
        "albumManagePrivilege": (int, 2),
    },
    "influencer": {
        "enabled": (bool, False),
        "maxVipNumbers": (int, 12),
        "maxVipMonthlyFee": (int, 500),
        "lock": (bool, False),
    },
    "topicCategories": {
        "enabled": (bool, False),
    },
    "externalContent": {
        "enabled": (bool, False),
    },
    "leaderboard": {
        "enabled": (bool, False),
    },
}


def _validate_module_field(mod_name: str, field: str, value):
    schema = MODULE_SCHEMA.get(mod_name)
    if schema is None or field not in schema:
        return False, None

    expected_type, _default = schema[field]

    if expected_type is bool:
        if not isinstance(value, bool):
            return False, None
        return True, value

    if expected_type is int:
        if isinstance(value, bool) or not isinstance(value, int):
            return False, None
        return True, value

    if expected_type == "module_info":
        if not isinstance(value, dict):
            return False, None
        cleaned = {}
        if "enabled" in value:
            if not isinstance(value["enabled"], bool):
                return False, None
            cleaned["enabled"] = value["enabled"]
        if "accessType" in value:
            if isinstance(value["accessType"], bool) or not isinstance(value["accessType"], int):
                return False, None
            cleaned["accessType"] = value["accessType"]
        if "minLevel" in value:
            if isinstance(value["minLevel"], bool) or not isinstance(value["minLevel"], int):
                return False, None
            cleaned["minLevel"] = value["minLevel"]
        return True, cleaned

    return False, None



@altacm.post("/altacm/s/community/x{ndcId}/modules")
@validauth_required
async def edit_community_modules(request: Request, ndcId: int):
    t1 = timestamp()
    trigger_uid = request.state.session["uid"]
    data = await request.json()

    modules_in = data.get("modules")
    if not isinstance(modules_in, dict) or not modules_in:
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()
    try:
        if not await _can_edit_community(db, ndcId, trigger_uid):
            return Errors.NotEnoughRights(timestamp() - t1)

        comms = db.get(table="Communities")
        community = await comms.find_one({"id": ndcId})
        if community is None:
            return Errors.DataNotExist(timestamp() - t1)

        set_ops = {}
        for mod_name, mod_val in modules_in.items():
            if mod_name not in MODULE_SCHEMA:
                return Errors.InvalidRequest(timestamp() - t1)

            if isinstance(mod_val, bool):
                set_ops[f"configuration.modules.{mod_name}.enabled"] = mod_val
                continue

            if not isinstance(mod_val, dict):
                return Errors.InvalidRequest(timestamp() - t1)

            for field, value in mod_val.items():
                ok, coerced = _validate_module_field(mod_name, field, value)
                if not ok:
                    return Errors.InvalidRequest(timestamp() - t1)

                set_ops[f"configuration.modules.{mod_name}.{field}"] = coerced

        if not set_ops:
            return Errors.InvalidRequest(timestamp() - t1)

        set_ops["modifiedTime"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        await comms.update_one({"id": ndcId}, {"$set": set_ops})
        updated = await comms.find_one({"id": ndcId})
    finally:
        db.close()

    return Base.Answer(
        {"community": await Communities.Info(updated, trigger_uid=trigger_uid)},
        spent_time=timestamp() - t1,
    )



@altacm.get("/altacm/s/community/x{ndcId}/modules/schema")
@validauth_required
async def get_modules_schema(request: Request, ndcId: int):
    t1 = timestamp()
    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    try:
        if not await _can_edit_community(db, ndcId, trigger_uid):
            return Errors.NotEnoughRights(timestamp() - t1)

        comms = db.get(table="Communities")
        community = await comms.find_one({"id": ndcId})
        if community is None:
            return Errors.DataNotExist(timestamp() - t1)

        mods = community.get("configuration", {}).get("modules", {})
    finally:
        db.close()

    schema_out = {}
    for mod_name, fields in MODULE_SCHEMA.items():
        cur = mods.get(mod_name, {}) if isinstance(mods.get(mod_name), dict) else {}
        field_defs = {}
        for field, (ftype, default) in fields.items():
            type_name = ftype if isinstance(ftype, str) else ftype.__name__
            # текущее значение по dot-path (avChat.videoEnabled)
            if "." in field:
                parent, child = field.split(".", 1)
                current = cur.get(parent, {}).get(child, default) if isinstance(cur.get(parent), dict) else default
            else:
                current = cur.get(field, default)
            field_defs[field] = {
                "type": type_name,
                "default": default,
                "current": current,
            }
        schema_out[mod_name] = field_defs

    return Base.Answer({"schema": schema_out}, spent_time=timestamp() - t1)



_KNOWN_PAGE_IDS = {
    "guidelines", "featured-default", "chat-default", "chat-public-chats",
    "post-latest-feed", "post-following-feed", "post-image-posts", "post-blogs",
    "post-questions", "post-polls", "catalog-default", "shared-folder",
    "topic-categories-default", "leaderboards-default",
}


def _validate_nav(items, custom_ids: set, allow_start: bool = False):
    if not isinstance(items, list):
        return False, None
    valid_ids = _KNOWN_PAGE_IDS | custom_ids
    cleaned = []
    for it in items:
        if not isinstance(it, dict) or "id" not in it:
            return False, None
        pid = it["id"]
        if not isinstance(pid, str) or pid not in valid_ids:
            return False, None
        entry = {"id": pid}
        if allow_start and it.get("isStartPage"):
            entry["isStartPage"] = True
        cleaned.append(entry)
    return True, cleaned


@altacm.post("/altacm/s/community/x{ndcId}/navigation")
@validauth_required
async def edit_community_navigation(request: Request, ndcId: int):
    t1 = timestamp()
    trigger_uid = request.state.session["uid"]
    data = await request.json()

    db = await Database().init()
    try:
        if not await _can_edit_community(db, ndcId, trigger_uid):
            return Errors.NotEnoughRights(timestamp() - t1)

        comms = db.get(table="Communities")
        community = await comms.find_one({"id": ndcId})
        if community is None:
            return Errors.DataNotExist(timestamp() - t1)

        custom_pages = (
            community.get("configuration", {}).get("pageCustomList", []) or []
        )
        custom_ids = {p.get("id") for p in custom_pages if isinstance(p, dict) and p.get("id")}

        set_ops = {}

        if "sidepanelTopNav" in data:
            ok, cleaned = _validate_nav(data["sidepanelTopNav"], custom_ids)
            if not ok:
                return Errors.InvalidRequest(timestamp() - t1)
            set_ops["configuration.sidepanelTopNav"] = cleaned

        if "sidepanelBottomNav" in data:
            ok, cleaned = _validate_nav(data["sidepanelBottomNav"], custom_ids)
            if not ok:
                return Errors.InvalidRequest(timestamp() - t1)
            set_ops["configuration.sidepanelBottomNav"] = cleaned

        if "homepageNav" in data:
            ok, cleaned = _validate_nav(data["homepageNav"], custom_ids, allow_start=True)
            if not ok:
                return Errors.InvalidRequest(timestamp() - t1)
            starts = [e for e in cleaned if e.get("isStartPage")]
            if len(starts) > 1:
                return Errors.InvalidRequest(timestamp() - t1)
            set_ops["configuration.homepageNav"] = cleaned

        if not set_ops:
            return Errors.InvalidRequest(timestamp() - t1)

        set_ops["modifiedTime"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        await comms.update_one({"id": ndcId}, {"$set": set_ops})
        updated = await comms.find_one({"id": ndcId})
    finally:
        db.close()

    return Base.Answer(
        {"community": await Communities.Info(updated, trigger_uid=trigger_uid)},
        spent_time=timestamp() - t1,
    )



from uuid import uuid4


@altacm.post("/altacm/s/community/x{ndcId}/page")
@validauth_required
async def add_community_page(request: Request, ndcId: int):
    t1 = timestamp()
    trigger_uid = request.state.session["uid"]
    data = await request.json()

    url = (data.get("url") or "").strip()
    if not url:
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()
    try:
        global_user = await db.get(table="Users").find_one({"id": trigger_uid})
        is_global = global_user and UserRole.is_global_staff(global_user.get("role", 0))
        is_allowed = is_global
        if not is_allowed:
            local_user = await db.get(f"x{ndcId}", "Users").find_one({"id": trigger_uid})
            if local_user and local_user.get("role", 0) in (
                UserRole.Leader,
                UserRole.Agent,
            ):
                is_allowed = True
        if not is_allowed:
            return Errors.NotEnoughRights(timestamp() - t1)

        comms = db.get(table="Communities")
        community = await comms.find_one({"id": ndcId})
        if community is None:
            return Errors.DataNotExist(timestamp() - t1)

        page = {
            "id": data.get("id") or str(uuid4()),
            "url": url,                              # https://... or ndc://...
            "alias": data.get("alias"),
            "originalTitle": data.get("originalTitle"),
            "parentId": data.get("parentId"),
        }

        await comms.update_one(
            {"id": ndcId},
            {
                "$push": {"configuration.pageCustomList": page},
                "$set": {"modifiedTime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")},
            },
        )
    finally:
        db.close()

    return Base.Answer({"page": page}, spent_time=timestamp() - t1)


@altacm.delete("/altacm/s/community/x{ndcId}/page/{pageId}")
@validauth_required
async def remove_community_page(request: Request, ndcId: int, pageId: str):
    t1 = timestamp()
    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    try:
        global_user = await db.get(table="Users").find_one({"id": trigger_uid})
        is_global = global_user and UserRole.is_global_staff(global_user.get("role", 0))
        is_allowed = is_global
        if not is_allowed:
            local_user = await db.get(f"x{ndcId}", "Users").find_one({"id": trigger_uid})
            if local_user and local_user.get("role", 0) in (
                UserRole.Leader,
                UserRole.Agent,
            ):
                is_allowed = True
        if not is_allowed:
            return Errors.NotEnoughRights(timestamp() - t1)

        comms = db.get(table="Communities")
        res = await comms.update_one(
            {"id": ndcId},
            {
                "$pull": {"configuration.pageCustomList": {"id": pageId}},
                "$set": {"modifiedTime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")},
            },
        )
        if res.modified_count == 0:
            return Errors.InvalidRequest(timestamp() - t1)
    finally:
        db.close()

    return Base.Answer({}, spent_time=timestamp() - t1)