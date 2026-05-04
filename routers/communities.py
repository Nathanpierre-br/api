from re import escape as regex_escape
from fastapi import APIRouter, Request
from time import time as timestamp

from objects import Base, Errors, Communities, User
from helpers.aioyaml import aioyaml
from helpers.functions import parse_page_token, calculate_page_tokens, is_app_link
from helpers.database.mongo import Database
from helpers.database.models import dttmn
from helpers.routers.cachable import CachableRoute
from helpers.decorators.validauth import validauth_required

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
    request: Request, start: int = 0, size: int = 25, pageToken: str | None = None
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
        table = await db.get(table="Users")
        row1 = await table.find_one({"id": uid})
        if row1 is None:
            return Errors.AccountNotExist(timestamp() - t1)

        # experimental ios freezing fix: giving full profile info
        table = await db.get("x0", "Users")
        row2 = await table.find_one({"id": uid})
        if row2 is None:
            return Errors.AccountNotExist(timestamp() - t1)

        table = await db.get(table="Communities")
        cl_needed = row1.get("communityList", [])[start : start + size]

        communityList = [
            await Communities.Info(item, db, uid) | {"membershipStatus": 1}
            async for item in table.find({"id": {"$in": cl_needed}})
        ]
        result = {
            "communityList": communityList,
            "userInfoInCommunities": {
                # experimental fix
                str(item): User.OwnNonSensetiveProfile(
                    row2, ndcId=item, membershipStatus=1
                )
                | {"joined": True, "membershipStatus": 1, "accountMembershipStatus": 1}
                for item in cl_needed
            },
            "tags": "fancysomemore",
            "paging": calculate_page_tokens(start, size, communityList),
            "showStoreBadge": False,
        }
    finally:
        await db.close()

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

    # parse page token
    if pageToken:
        start = parse_page_token(pageToken, start)

    uid = request.state.session["uid"]
    db = await Database().init()
    try:
        table = await db.get(table="Communities")

        query = {"name": {"$regex": regex_escape(q), "$options": "i"}, "lang": language}
        items = [item async for item in table.find(query).skip(start).limit(size)]
        communityList = [await Communities.Info(item, db, uid) for item in items]
        return Base.Answer(
            {
                "communityList": communityList,
                "paging": calculate_page_tokens(start, size, communityList),
                "allItemCount": len(items),
            },
            spent_time=timestamp() - t1,
        )
    finally:
        await db.close()


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
    uid = request.state.session["uid"]
    start = parse_page_token(pageToken, start)

    db = await Database().init()
    try:
        table = await db.get(table="Communities")

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
        await db.close()


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

    # parse page token
    if pageToken:
        start = parse_page_token(pageToken, start)

    if is_app_link(q) and "/c/" in q:
        q = q[q.find("/c/") + 3 :]

    uid = request.state.session["uid"]
    db = await Database().init()
    try:
        table = await db.get(table="Communities")

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
        await db.close()


# community join
@communities.post("/x{ndcId}/s/community/join")
async def join_community(request: Request, ndcId: int):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession()

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    try:
        # checking if user is banned globally
        table_accounts = await db.get(table="Users")
        account = await table_accounts.find_one({"id": trigger_uid})
        if account and account.get("status") == 9:
            return Errors.UserBanned(timestamp() - t1)

        table_communities = await db.get(table="Communities")
        community = await table_communities.find_one({"id": ndcId})
        if not community:
            return Errors.DataNotExist(timestamp() - t1)

        # updating community info
        if trigger_uid in community.get("memberList", []):
            return Base.Answer(
                {"api:warning": "You are already joined community."},
                spent_time=timestamp() - t1,
            )

        # adding profile info if not exist
        table_community_users = await db.get(f"x{ndcId}", "Users")
        user_info = await table_community_users.find_one({"id": trigger_uid})

        if user_info and user_info.get("status") == 9:
            return Errors.UserBanned(timestamp() - t1)

        if not user_info:
            g_table = await db.get("x0", "Users")
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
                if new_profile["role"] not in [200, 201, 253, 254, 555]
                else new_profile["role"]
            )
            for field in ["_id", "createdTime", "modifiedTime"]:
                new_profile.pop(field, None)

            new_timestamp = dttmn()
            new_profile["createdTime"] = new_timestamp
            new_profile["modifiedTime"] = new_timestamp

            await table_community_users.insert_one(new_profile)

        # update community profile that user joined
        await table_community_users.update_one(
            {"id": trigger_uid}, {"$set": {"status": 0}}
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
        table_global_users = await db.get(table="Users")
        await table_global_users.update_one(
            {"id": trigger_uid}, {"$addToSet": {"communityList": ndcId}}
        )

        return Base.Answer({}, spent_time=timestamp() - t1)
    except Exception as e:
        print(f"Error in join_community: {e}")
        return Errors.InternalServerError(timestamp() - t1)
    finally:
        await db.close()


# community leave
@communities.post("/x{ndcId}/s/community/leave")
async def leave_community(request: Request, ndcId: int):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession()

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    try:
        table_communities = await db.get(table="Communities")
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
        table_global_users = await db.get(table="Users")
        await table_global_users.update_one(
            {"id": trigger_uid}, {"$pull": {"communityList": ndcId}}
        )

        # update community user info
        table_xndc_users = await db.get(f"x{ndcId}", "Users")
        user_info = await table_xndc_users.find_one({"id": trigger_uid})
        role = (
            0
            if not user_info or user_info["role"] not in [200, 201, 555]
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
        await db.close()


# get community info
# [GET] /g/s/community/{ndcId}


@communities.get("/g/s/community/info")
@communities.get("/x{ndcId}/s/community/info")
@communities.get("/g/s-x{ndcId}/community/info")
async def get_community_info(ndcId: int, request: Request):
    t1 = timestamp()

    uid = request.state.session["uid"]

    db = await Database().init()
    try:
        ndc_info = await Communities.Info(ndcId, db, uid)
        if not ndc_info:
            return Errors.DataNotExist(timestamp() - t1)

        users_table = await db.get(f"x{ndcId}", "Users")
        user_info = await users_table.find_one({"id": uid})
        if not user_info:
            full_user_data = {"api:warning": "User not joined or profile is corrupted."}
        else:
            full_user_data = User.GetUserInfo(user_info, triggerUserId=uid, ndcId=ndcId)

        return Base.Answer(
            {
                "community": ndc_info,
                "isCurrentUserJoined": bool(ndc_info.get("membershipStatus")),
                "currentUserInfo": {
                    "userProfile": {
                        "id": uid,
                        "membershipStatus": ndc_info.get("membershipStatus", 0),
                    }
                    | full_user_data,
                },
            },
            spent_time=timestamp() - t1,
        )
    finally:
        await db.close()


# guidelines
@communities.get("/g/s/community/official-guideline")
@communities.get("/x{ndcId}/s/community/official-guideline")
async def get_official_guidelines(
    request: Request, ndcId: int = 0, language: str = "en"
):
    try:
        file = await aioyaml("files/guidelines.yaml")
        language = language.lower() if language.lower() in ["ru", "en"] else "en"
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
        table = await db.get(table="Communities")
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
        await db.close()


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
                "userProfileCount": 0,  # temm
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
        table = await db.get(f"x{ndcId}", "Users")

        items = [
            User.OwnNonSensetiveProfile(item, ndcId=ndcId, membershipStatus=1)
            async for item in table.find(query)
            .skip(start)
            .limit(size)
            .sort({"createdTime": -1})
        ]

        return Base.Answer(
            {
                "userProfileCount": 0,  # temm
                "userProfileList": items,
            },
            spent_time=timestamp() - t1,
        )
    finally:
        await db.close()


@communities.get("/g/s/user-group/{userGroupType}")
@communities.get("/x{ndcId}/s/user-group/{userGroupType}")
async def get_user_groups(request: Request, userGroupType: str, ndcId: int = 0):
    # dont reallt know why they need em except featured users
    return Base.Answer({"userProfileList": []})


@communities.get("/g/s/live-layer")
@communities.get("/x{ndcId}/s/live-layer")
async def live_layer_topic(request: Request, ndcId: int = 0, topic: str | None = None):
    if topic is not None:
        return Base.Answer(Base.LiveLayerTopic(topic))

    return Errors.InvalidRequest()


@communities.get("/g/s/live-layer/homepage")
@communities.get("/x{ndcId}/s/live-layer/homepage")
async def live_layer(request: Request, ndcId: int = 0, topic: str | None = None):
    return Base.Answer(
        {
            "liveLayerList": [
                Base.LiveLayerTopic(f"ndtopic:x{ndcId}:{t}")
                for t in ["online-members", "watching"]
            ]
        }
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
async def get_leaders_choice(ndcId: int, request: Request):
    return Base.Answer()
