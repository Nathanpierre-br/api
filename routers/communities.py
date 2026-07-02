from re import escape as regex_escape
from time import time as timestamp
from pymongo import DESCENDING
from fastapi import APIRouter, Request
from datetime import datetime

from helpers.aioyaml import aioyaml
from helpers.database.models import dttmn
from helpers.database.mongo import Database
from helpers.decorators.turtlelimit import TurtleTime, turtlelimiter
from helpers.decorators.validauth import validauth_required
from helpers.functions import calculate_page_tokens, is_app_link, parse_page_token
from helpers.routers.cachable import CachableRoute
from objects import Base, Communities, Errors, User
from objects.types import UserGroupType
from helpers.database.redis import get as get_redis

communities = APIRouter()
communities.route_class = CachableRoute


@communities.get("/g/s/chat/thread-check/human-readable")
async def humanreadable(request: Request, ndcIds: str = ""):
    chunks = ndcIds.split(",")

    return Base.Answer(
        {
            "treatedNdcIds": [int(chunk) for chunk in chunks],
            "threadCheckResultInCommunities": {chunk: [] for chunk in chunks},
        }
    )


# communities you currently in
@communities.get("/g/s/community/joined")
async def joined_communities(
    request: Request, start: int = 0, size: int = 25, pageToken: str | None = None, q: str = ""
):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Base.Answer(
            {
                "communityList": [],
                "userInfoInCommunities": {},
                "showStoreBadge": False,
            },
            spent_time=timestamp() - t1,
        )
    # parse page token
    if pageToken:
        start = parse_page_token(pageToken, start)
    uid = request.state.session["uid"]
    size = size if 0 < size < 101 else 25
    db = await Database().init()
    try:
        table = db.get(table="Users")
        row1 = await table.find_one({"id": uid})
        if row1 is None:
            return Errors.AccountNotExist(timestamp() - t1)
        # experimental ios freezing fix: giving full profile info
        table = db.get("x0", "Users")
        row2 = await table.find_one({"id": uid})
        if row2 is None:
            return Errors.AccountNotExist(timestamp() - t1)

        table = db.get(table="Communities")
        all_joined_ids = row1.get("communityList", [])

        q = q.strip()
        if q:
            # фильтруем id по совпадению имени, сохраняя исходный порядок
            matched_cursor = table.find(
                {
                    "id": {"$in": all_joined_ids},
                    "name": {"$regex": regex_escape(q), "$options": "i"},
                },
                {"id": 1},
            )
            matched_ids = {doc["id"] async for doc in matched_cursor}
            filtered_ids = [ndcId for ndcId in all_joined_ids if ndcId in matched_ids]
        else:
            filtered_ids = all_joined_ids

        cl_needed = filtered_ids[start : start + size]

        items_by_id = {}
        async for item in table.find({"id": {"$in": cl_needed}}):
            info = await Communities.Info(item, db, uid) | {"membershipStatus": 1}
            items_by_id[item["id"]] = info

        communityList = [
            items_by_id[ndcId] for ndcId in cl_needed if ndcId in items_by_id
        ]

        result = {
            "communityList": communityList,
            "userInfoInCommunities": {
                str(item): {
                    "userProfile": User.OwnNonSensetiveProfile(
                        row2, ndcId=item, membershipStatus=1
                    )
                }
                | {"joined": True, "membershipStatus": 1, "accountMembershipStatus": 1}
                for item in cl_needed
            },
            "tags": "fancysomemore",
            "paging": calculate_page_tokens(start, size, communityList),
            "showStoreBadge": False,
        }
    finally:
        db.close()
    # print(result)
    return Base.Answer(
        result,
        spent_time=timestamp() - t1,
    )

# communities search
@communities.get("/g/s/community/search")
async def search_community(
    request: Request,
    q: str = "",
    start: int = 0,
    size: int = 25,
    pageToken: str | None = None,
    language: str = "en",
):
    t1 = timestamp()
    size = size if 0 < size < 101 else 25
    if pageToken:
        start = parse_page_token(pageToken, start)

    uid = request.state.session["uid"]
    db = await Database().init()
    try:
        table = db.get(table="Communities")
        query = {
            "name": {"$regex": regex_escape(q.strip()), "$options": "i"},
            "lang": language,
            "hidden": {"$ne": True},
        }
        total_count = await table.count_documents(query)
        items = [item async for item in table.find(query).skip(start).limit(size)]
        communityList = [await Communities.Info(item, db, uid) for item in items]
        return Base.Answer(
            {
                "communityList": communityList,
                "paging": calculate_page_tokens(start, size, communityList),
                "allItemCount": total_count,
            },
            spent_time=timestamp() - t1,
        )
    finally:
        db.close()

# all communities available
@communities.get("/g/s/topic/0/feed/community")
@communities.get("/g/s/community/trending")
@communities.get("/g/s/community/suggested")
async def all_communities_list(
    request: Request,
    language: str = "en",
    size: int = 25,
    start: int = 0,
    pageToken: str | None = None,
):
    t1 = timestamp()
    uid = request.state.session.get("uid")
    start = parse_page_token(pageToken, start)

    db = await Database().init()
    try:
        table = db.get(table="Communities")

        items = [
            item
            async for item in table.find({"lang": language}).skip(start).limit(size)
        ]
        communityList = [await Communities.Info(item, db, uid) for item in items]
        return Base.Answer(
            {
                "communityList": communityList,
                "paging": calculate_page_tokens(start, size, communityList),
            },
            spent_time=timestamp() - t1,
        )
    finally:
        db.close()


# community search by aminoid
@communities.get("/g/s/search/amino-id-and-link")
async def search_community_by_amino_id(
    request: Request,
    q: str = "",
    start: int = 0,
    size: int = 25,
    pageToken: str | None = None,
):
    t1 = timestamp()
    size = size if 0 < size < 101 else 25
    if pageToken:
        start = parse_page_token(pageToken, start)

    q = q.strip()

    if is_app_link(q) and "/c/" in q:
        q = q[q.find("/c/") + 3:]
        q = q.split("/")[0].split("?")[0].strip()

    if not q:
        return Base.Answer(
            {"resultList": [], "paging": calculate_page_tokens(start, size, [])},
            spent_time=timestamp() - t1,
        )

    uid = request.state.session["uid"]
    db = await Database().init()
    try:
        table = db.get(table="Communities")
        query = {"aminoId": {"$regex": regex_escape(q), "$options": "i"}}
        items = [item async for item in table.find(query).skip(start).limit(size)]
        communityList = [
            {"refObject": await Communities.Info(item, db, uid)} for item in items
        ]
        return Base.Answer(
            {
                "resultList": communityList,
                "paging": calculate_page_tokens(start, size, communityList),
            },
            spent_time=timestamp() - t1,
        )
    finally:
        db.close()


# community join
@communities.post("/x{ndcId}/s/community/join")
@turtlelimiter(limit=1, period=TurtleTime.second, tag="jl-community")
async def join_community(request: Request, ndcId: int):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession()

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    try:
        # checking if user is banned globally
        table_accounts = db.get(table="Users")
        account = await table_accounts.find_one({"id": trigger_uid})
        if account and account.get("status") == 9:
            return Errors.UserBanned(timestamp() - t1)

        table_communities = db.get(table="Communities")
        community = await table_communities.find_one({"id": ndcId})
        if not community:
            return Errors.DataNotExist(timestamp() - t1)

        # adding profile info if not exist
        table_community_users = db.get(f"x{ndcId}", "Users")
        user_info = await table_community_users.find_one({"id": trigger_uid})

        if user_info and user_info.get("status") == 9:
            return Errors.UserBanned(timestamp() - t1)

        if not user_info:
            g_table = db.get("x0", "Users")
            g_data = await g_table.find_one({"id": trigger_uid})
            if not g_data:
                return Errors.AccountNotExist(timestamp() - t1)

            # prepare new profile data
            new_profile = g_data.copy()
            new_profile["whoFollows"] = []
            new_profile["following"] = []
            new_profile["wall"] = {}
            new_profile["role"] = (
                0
                if new_profile["role"] not in [200, 201, 254, 555]
                else new_profile["role"]
            )
            for field in ["_id", "createdTime", "modifiedTime"]:
                new_profile.pop(field, None)

            new_timestamp = dttmn()
            new_profile["createdTime"] = new_timestamp
            new_profile["modifiedTime"] = new_timestamp

            await table_community_users.insert_one(new_profile)
            user_info = new_profile

        # update community profile that user joined
        await table_community_users.update_one(
            {"id": trigger_uid}, {"$set": {"status": 0}}
        )

        if account.get("isVerified"):
            await table_community_users.update_one(
                {"id": trigger_uid},
                {"$set": {"isVerified": True, "tagList": account.get("tagList", [])}},
            )

        # update community
        await table_communities.update_one(
            {"id": ndcId},
            [
                {
                    "$set": {
                        "memberList": {
                            "$setUnion": [
                                {"$ifNull": ["$memberList", []]},
                                [trigger_uid],
                            ]
                        }
                    }
                },
                {"$set": {"membersCount": {"$size": "$memberList"}}},
            ],
        )

        # update global user info
        table_global_users = db.get(table="Users")
        await table_global_users.update_one(
            {"id": trigger_uid}, {"$addToSet": {"communityList": ndcId}}
        )

        return Base.Answer(
            {"userProfile": User.OwnNonSensetiveProfile(user_info)},
            spent_time=timestamp() - t1,
        )
    except Exception as e:
        print(f"Error in join_community: {e}")
        return Errors.InternalServerError(timestamp() - t1)
    finally:
        db.close()


# community leave
@communities.post("/x{ndcId}/s/community/leave")
@turtlelimiter(limit=1, period=TurtleTime.second, tag="jl-community")
async def leave_community(request: Request, ndcId: int):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession()

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    try:
        table_communities = db.get(table="Communities")
        community = await table_communities.find_one({"id": ndcId})

        if not community:
            return Errors.DataNotExist(timestamp() - t1)

        if trigger_uid == community.get("agent") or ndcId == 0:
            return Errors.NotEnoughRights(timestamp() - t1)

        if trigger_uid not in community.get("memberList", []):
            return Base.Answer(
                {"api:warning": "You was never part of this community."},
                spent_time=timestamp() - t1,
            )

        # Update community: remove member
        await table_communities.update_one(
            {"id": ndcId},
            [
                {
                    "$set": {
                        "memberList": {
                            "$setDifference": [
                                {"$ifNull": ["$memberList", []]},
                                [trigger_uid],
                            ]
                        }
                    }
                },
                {"$set": {"membersCount": {"$size": "$memberList"}}},
            ],
        )

        # update global user info
        table_global_users = db.get(table="Users")
        await table_global_users.update_one(
            {"id": trigger_uid}, {"$pull": {"communityList": ndcId}}
        )

        # update community user info
        table_xndc_users = db.get(f"x{ndcId}", "Users")
        user_info = await table_xndc_users.find_one({"id": trigger_uid})
        role = (
            0
            if not user_info or user_info["role"] not in [200, 201, 254, 555]
            else user_info["role"]
        )
        await table_xndc_users.update_one(
            {"id": trigger_uid}, {"$set": {"role": role, "status": 5}}
        )

        return Base.Answer({}, spent_time=timestamp() - t1)
    except Exception as e:
        print(f"Error in leave_community: {e}")
        return Errors.InternalServerError(timestamp() - t1)
    finally:
        db.close()


# get community info
# [GET] /g/s/community/{ndcId}


@communities.get("/g/s/community/info")
@communities.get("/x{ndcId}/s/community/info")
@communities.get("/g/s-x{ndcId}/community/info")
async def get_community_info(request: Request, ndcId: int = 0):
    t1 = timestamp()

    try:uid = request.state.session["uid"]
    except:uid=None
    db = await Database().init()
    try:
        ndc_info = await Communities.Info(ndcId, db, uid)
        if not ndc_info:
            return Errors.DataNotExist(timestamp() - t1)

        users_table = db.get(f"x{ndcId}", "Users")
        user_info = await users_table.find_one({"id": uid})
        if not user_info:
            full_user_data = None
        else:
            full_user_data = User.GetUserInfo(user_info, triggerUserId=uid, ndcId=ndcId)

        return Base.Answer(
            {
                "community": ndc_info,
                "isCurrentUserJoined": bool(ndc_info.get("membershipStatus", 0)),
                "currentUserInfo": (full_user_data or {})
                | {"membershipStatus": ndc_info.get("membershipStatus", 0)},
            },
            spent_time=timestamp() - t1,
        )
    finally:
        db.close()


# guidelines
@communities.get("/g/s/community/official-guideline")
@communities.get("/x{ndcId}/s/community/official-guideline")
async def get_official_guidelines(
    request: Request, ndcId: int = 0, language: str = "en"
):
    try:
        file = await aioyaml("files/guidelines.yaml")
        language = language.lower() if language.lower() in ["ru", "en", "ar", "es"] else "en"
        # we should also think about not hardcoding ndc langs
        guideline = file[language]
    except Exception as e:
        print("Cant get official guidelines via yaml!:", e)
        guideline = "[b]Oh no!\nSomething went wrong. Please try again later."
        # maybe do not hardcode strings? we can parse ndclang, lookup i18n...

    return Base.Answer(
        {
            "officialGuideline": {
                "content": guideline,
                "mediaList": [],
            },
        },
    )


@communities.get("/g/s/community/guideline")
@communities.get("/x{ndcId}/s/community/guideline")
@communities.get("/g/s-x{ndcId}/community/guideline")
async def get_community_guidelines(request: Request, ndcId: int = 0):
    t1 = timestamp()

    db = await Database().init()
    try:
        table = db.get(table="Communities")
        info = await table.find_one({"id": ndcId})

        if not info:
            return Errors.DataNotExist(timestamp() - t1)

        return Base.Answer(
            {
                "communityGuideline": {
                    "content": info.get("guideline", ""),
                    "mediaList": [],
                }
            },
            spent_time=timestamp() - t1,
        )
    finally:
        db.close()


@communities.get("/x{ndcId}/s/user-profile")
async def get_community_profiles(
    ndcId: int,
    request: Request,
    start: int = 0,
    size: int = 25,
    type: str = "",
):
    if type == "featured":
        return Base.Answer(
            {
                "userProfileCount": 0,
                "userProfileList": [],
            },
        )

    t1 = timestamp()
    size = size if 0 < size < 101 else 25

    queries = {
        "leaders": {"role": {"$in": [102, 100]}},
        "curators": {"role": 101},
        "recent": {},
        "summary": {},
    }

    query = queries.get(type)
    if query is None:
        return Errors.InvalidRequest()

    db = await Database().init()
    try:
        table = db.get(f"x{ndcId}", "Users")

        items = [
            User.OwnNonSensetiveProfile(item, ndcId=ndcId, membershipStatus=1)
            async for item in table.find(query)
                .skip(start)
                .limit(size)
                .sort([("role", DESCENDING), ("createdTime", -1)])
        ]
        return Base.Answer(
            {
                "userProfileCount": 0,
                "userProfileList": items,
            },
            spent_time=timestamp() - t1,
        )
    finally:
        db.close()




@communities.get("/g/s/user-group/{userGroupType}")
@communities.get("/x{ndcId}/s/user-group/{userGroupType}")
async def get_user_groups(
    request: Request,
    userGroupType: str,
    ndcId: int = 0,
    start: int = 0,
    size: int = 20,
    stoptime: str | None = None,
):
    t1 = timestamp()
    if userGroupType != UserGroupType.QuickAccess:
        return Base.Answer({"userProfileList": []}, spent_time=timestamp() - t1)

    size = size if 0 < size < 101 else 20
    uid = request.state.session["uid"]
    db = await Database().init()
    try:
        table = db.get(f"x{ndcId}", "Users")
        row = await table.find_one({"id": uid})
        if row is None:
            return Errors.AccountNotExist(timestamp() - t1)

        favEntries = row.get("quickAccessList", [])
        favEntries = [
            e if isinstance(e, dict) else {"id": e, "addedAt": ""}
            for e in favEntries
        ]

        if stoptime:
            favEntries = [e for e in favEntries if e.get("addedAt", "") < stoptime]

        pageEntries = favEntries[start : start + size]
        favIds = [e["id"] for e in pageEntries]

        if not favIds:
            return Base.Answer({"userProfileList": []}, spent_time=timestamp() - t1)

        users_by_id = {}
        async for u in table.find({"id": {"$in": favIds}}):
            users_by_id[u["id"]] = User.GetUserInfo(u, ndcId=ndcId)

        userProfileList = [
            users_by_id[fid] for fid in favIds if fid in users_by_id
        ]
    finally:
        db.close()

    return Base.Answer({"userProfileList": userProfileList}, spent_time=timestamp() - t1)



@communities.post("/g/s/user-group/{userGroupType}/position")
@communities.post("/x{ndcId}/s/user-group/{userGroupType}/position")
async def reorder_user_group(request: Request, userGroupType: str, ndcId: int = 0):
    t1 = timestamp()
    if userGroupType != UserGroupType.QuickAccess:
        return Errors.InvalidRequest(timestamp() - t1)

    try:
        data = await request.json()
        uidList = data["uidList"]
        if not isinstance(uidList, list):
            return Errors.InvalidRequest(timestamp() - t1)
    except Exception:
        return Errors.InvalidRequest(timestamp() - t1)

    uid = request.state.session["uid"]
    db = await Database().init()
    try:
        table = db.get(f"x{ndcId}", "Users")
        row = await table.find_one({"id": uid})
        if row is None:
            return Errors.AccountNotExist(timestamp() - t1)

        favEntries = row.get("quickAccessList", [])
        favEntries = [
            e if isinstance(e, dict) else {"id": e, "addedAt": ""}
            for e in favEntries
        ]

        entries_by_id = {e["id"]: e for e in favEntries}

        seen = set()
        new_front = []
        for target_id in uidList:
            if target_id in entries_by_id and target_id not in seen:
                new_front.append(entries_by_id[target_id])
                seen.add(target_id)

        remaining = [e for e in favEntries if e["id"] not in seen]
        new_order = new_front + remaining

        await table.update_one({"id": uid}, {"$set": {"quickAccessList": new_order}})
    finally:
        db.close()

    return Base.Answer({}, spent_time=timestamp() - t1)




@communities.post("/g/s/user-group/{userGroupType}/{targetId}")
@communities.post("/x{ndcId}/s/user-group/{userGroupType}/{targetId}")
async def add_to_user_group(request: Request, userGroupType: str, targetId: str, ndcId: int = 0):
    t1 = timestamp()
    if userGroupType != UserGroupType.QuickAccess:
        return Errors.InvalidRequest(timestamp() - t1)

    uid = request.state.session["uid"]
    db = await Database().init()
    try:
        table = db.get(f"x{ndcId}", "Users")
        row = await table.find_one({"id": uid})
        if row is None:
            return Errors.AccountNotExist(timestamp() - t1)

        target = await table.find_one({"id": targetId})
        if target is None:
            return Errors.AccountNotExist(timestamp() - t1)

        existing = row.get("quickAccessList", [])
        existing_ids = {
            (e["id"] if isinstance(e, dict) else e) for e in existing
        }
        if targetId in existing_ids:
            return Base.Answer({}, spent_time=timestamp() - t1) 

        entry = {
            "id": targetId,
            "addedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        await table.update_one({"id": uid}, {"$push": {"quickAccessList": entry}})
    finally:
        db.close()

    return Base.Answer({}, spent_time=timestamp() - t1)


@communities.delete("/g/s/user-group/{userGroupType}/{targetId}")
@communities.delete("/x{ndcId}/s/user-group/{userGroupType}/{targetId}")
async def remove_from_user_group(request: Request, userGroupType: str, targetId: str, ndcId: int = 0):
    t1 = timestamp()
    if userGroupType != UserGroupType.QuickAccess:
        return Errors.InvalidRequest(timestamp() - t1)

    uid = request.state.session["uid"]
    db = await Database().init()
    try:
        table = db.get(f"x{ndcId}", "Users")
        row = await table.find_one({"id": uid})
        if row is None:
            return Errors.AccountNotExist(timestamp() - t1)

        await table.update_one(
            {"id": uid},
            {"$pull": {"quickAccessList": targetId}},
        )
        await table.update_one(
            {"id": uid},
            {"$pull": {"quickAccessList": {"id": targetId}}},
        )
    finally:
        db.close()

    return Base.Answer({}, spent_time=timestamp() - t1)







async def _get_online_uids(ndcId: int) -> list[str]:
    redis = get_redis()
    key = f"x{ndcId}:online"
    members = await redis.smembers(key)
    return [m.decode() if isinstance(m, bytes) else m for m in members]
 
 
async def _get_profiles_for_live_layer(ndcId: int, uids: list[str]) -> list[dict]:
    if not uids:
        return []
    db = await Database().init()
    try:
        table = db.get(f"x{ndcId}", "Users")
        profiles = []
        async for row in table.find({"id": {"$in": uids}}):
            profiles.append(User.OwnNonSensetiveProfile(row, ndcId=ndcId, membershipStatus=1))
        return profiles
    finally:
        db.close()
 



@communities.get("/g/s/live-layer")
@communities.get("/x{ndcId}/s/live-layer")
async def live_layer_topic(request: Request, ndcId: int = 0, topic: str | None = None):
    if topic is None:
        return Errors.InvalidRequest()

    effective_ndcId = ndcId
    if not effective_ndcId and topic:
        parts = topic.split(":")
        if len(parts) >= 2:
            ndc_part = parts[1]
            if ndc_part.startswith("x"):
                try:
                    effective_ndcId = int(ndc_part[1:])
                except ValueError:
                    pass
 
    uids = await _get_online_uids(effective_ndcId)
    profiles = await _get_profiles_for_live_layer(effective_ndcId, uids)
 
    return Base.Answer(Base.LiveLayerTopic(
        topic_name=topic,
        users_count=len(profiles),
        users_list=profiles,
    ))
 

@communities.get("/g/s/live-layer/homepage")
@communities.get("/x{ndcId}/s/live-layer/homepage")
async def live_layer(request: Request, ndcId: int = 0):
    uids = await _get_online_uids(ndcId)
    profiles = await _get_profiles_for_live_layer(ndcId, uids)

    return Base.Answer(
        {
            "liveLayerList": [
                Base.LiveLayerTopic(
                    topic_name=f"ndtopic:x{ndcId}:online-members",
                    users_count=len(profiles),
                    users_list=profiles,
                ),
                Base.LiveLayerTopic(
                    topic_name=f"ndtopic:x{ndcId}:watching",
                ),
            ]
        }
    )


@communities.post("/g/s/community/joined/reorder")
async def reorder_communities(request: Request):
    t1 = timestamp()
    uid = request.state.session["uid"]
    data = await request.json()
    ndcIdList = data.get("ndcIdList", [])
    if not ndcIdList:
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()
    try:
        table = db.get(table="Users")
        row1 = await table.find_one({"id": uid})
        if row1 is None:
            return Errors.AccountNotExist(timestamp() - t1)

        current_order = row1.get("communityList", [])

        new_front = [ndcId for ndcId in ndcIdList if ndcId in current_order]
        new_front_set = set(new_front)

        remaining = [ndcId for ndcId in current_order if ndcId not in new_front_set]

        new_order = new_front + remaining

        await table.update_one({"id": uid}, {"$set": {"communityList": new_order}})
    finally:
        db.close()

    return Base.Answer(
        spent_time=timestamp() - t1,
    )





# looks like this request allows precheck if you can do it
# for now it will be mocked
# GET /api/v1/x1/s/user-profile/de838eb4-312c-4ba0-9d81-9aad3fc984e1/compose-eligible-check?objectType=chat-thread&objectSubtype=public
@communities.get("/x{ndcId}/s/user-profile/{uid}/compose-eligible-check")
@validauth_required
async def compose_eligible_check(request: Request, ndcId: int, uid: str):
    trigger_uid = request.state.session["uid"]
    if trigger_uid != uid:
        return Errors.InvalidRequest()

    return Base.Answer()


# leaders choice
@communities.get("/g/s/community/kindred")
@communities.get("/x{ndcId}/s/community/kindred")
@communities.get("/g/s-x{ndcId}/community/kindred")
async def get_leaders_choice(request: Request, ndcId: int = 0):
    return Base.Answer()





@communities.get("/x{ndcId}/s/community/user-titles")
async def get_community_titles(request: Request, ndcId: int = 0):
    t1 = timestamp()
    db = await Database().init()
    titles = []
    try:
        table = db.get(f"x{ndcId}", "Users")
        user = await table.find_one({})
        titles = user.get("titles", []) if user else []
    finally:
        db.close()
    return Base.Answer({"userTitleList": titles}, spent_time=timestamp() - t1)