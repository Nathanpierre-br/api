from base64 import b85encode, b85decode
from re import escape as regex_escape
from fastapi import APIRouter, Request
from time import time as timestamp
# from aiofiles import open as asyncopen

from objects import Base, Errors, Communities, User
from helpers.aioyaml import aioyaml
from helpers.database.mongo import Database
from helpers.database.models import dttmn
from helpers.routers.cachable import CachableRoute

communities = APIRouter()
communities.route_class = CachableRoute


# communities you currently in
@communities.get("/g/s/community/joined")
async def joined_communities(request: Request, start: int = 0, size: int = 25):
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

    uid = request.state.session["uid"]
    size = size if 0 < size < 101 else 25

    db = await Database().init()
    try:
        table = await db.get(table="Users")
        row1 = await table.find_one({"id": uid})
        if row1 is None:
            return Errors.AccountNotExist(timestamp() - t1)

        table = await db.get(table="Communities")

        return Base.Answer(
            {
                "communityList": [
                    await Communities.Info(item, db, uid)
                    async for item in table.find(
                        {
                            "id": {
                                "$in": row1.get("communityList", [])[
                                    start : start + size
                                ]
                            }
                        }
                    )
                ],
                "userInfoInCommunities": {
                    # experimental fix
                    str(item): {"membershipStatus": 1, "id": uid}
                    for item in row1.get("communityList", [])[start : start + size]
                },
                "showStoreBadge": False,
            },
            spent_time=timestamp() - t1,
        )
    finally:
        await db.close()


# communities search
@communities.get("/g/s/community/search")
async def search_community(
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
        try:
            decoded = b85decode(pageToken).decode()
            start = max(0, int(decoded) if decoded.isdigit() else 0)
        except Exception:
            pass

    uid = request.state.session["uid"]
    db = await Database().init()
    try:
        table = await db.get(table="Communities")

        query = {"name": {"$regex": regex_escape(q), "$options": "i"}}
        items = [item async for item in table.find(query).skip(start).limit(size)]

        return Base.Answer(
            {
                "communityList": [
                    await Communities.Info(item["id"], db, uid) for item in items
                ],
                "paging": {
                    "nextPageToken": b85encode(str(size + start).encode()).decode(),
                    "prevPageToken": b85encode(
                        ("0" if start - size <= 0 else str(start - size)).encode()
                    ).decode(),
                },
                "allItemCount": len(items),
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
        if not (await table_community_users.find_one({"id": trigger_uid})):
            g_table = await db.get("x0", "Users")
            g_data = await g_table.find_one({"id": trigger_uid})
            if not g_data:
                return Errors.AccountNotExist(timestamp() - t1)

            # prepare new profile data
            new_profile = g_data.copy()
            new_profile["whoFollows"] = []
            new_profile["following"] = []
            new_profile["wall"] = {}
            for field in ["_id", "createdTime", "modifiedTime"]:
                new_profile.pop(field, None)

            new_timestamp = dttmn()
            new_profile["createdTime"] = new_timestamp
            new_profile["modifiedTime"] = new_timestamp

            await table_community_users.insert_one(new_profile)

        # update community
        await table_communities.update_one(
            {"id": ndcId},
            [
                {"$set": {"memberList": {"$setUnion": ["$memberList", [trigger_uid]]}}},
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
                        "memberList": {"$setDifference": ["$memberList", [trigger_uid]]}
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
        table_global_users = await db.get(f"x{ndcId}", "Users")
        await table_global_users.update_one(
            {"id": trigger_uid}, {"$set": {"role": 0, "status": 1}}
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
        info = await Communities.Info(ndcId, db, uid)
        if not info:
            return Errors.DataNotExist(timestamp() - t1)

        return Base.Answer({"community": info}, spent_time=timestamp() - t1)
    finally:
        await db.close()


# guidelines
@communities.get("/g/s/community/official-guideline")
@communities.get("/x{ndcId}/s/community/official-guideline")
async def get_official_guidelines(ndcId: int, request: Request, language: str = "en"):
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
                "communityGuideline": {
                    "content": guideline,
                    "mediaList": [],
                }
            },
        )
    except Exception:
        return Errors.InternalServerError()


@communities.get("/g/s/community/guideline")
@communities.get("/x{ndcId}/s/community/guideline")
@communities.get("/g/s-x{ndcId}/community/guideline")
async def get_community_guidelines(ndcId: int, request: Request):
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
