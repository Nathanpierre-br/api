import random
from json import dumps
from datetime import UTC, datetime, timedelta
from re import escape as regex_escape
from time import time as timestamp
from uuid import uuid4

from fastapi import APIRouter, Request
from pymongo import DESCENDING

from helpers.daily_settlement import (
    CHECKIN_COIN_REWARDS,
    CHECKIN_COIN_WEIGHTS,
    LOTTERY_REWARDS,
    LOTTERY_WEIGHTS,
    date_str as _date_str,
    earned_rep as _earned_rep,
    get_tz as _get_tz,
    local_date as _local_date,
    settle_user_active_coins,
)
from helpers.database.models import Community, ModelFabric
from helpers.database.mongo import Database
from helpers.decorators.turtlelimit import TurtleTime, turtlelimiter
from helpers.functions import calculate_page_tokens, parse_page_token
from helpers.routers.cachable import CachableRoute
from objects import Base, Comments, Errors, User

profile_methods = APIRouter()
profile_methods.route_class = CachableRoute


@profile_methods.post("/g/s/account/change-amino-id")
@turtlelimiter(limit=1, period=TurtleTime.minute, tag="amino-id-change")
async def change_aminoId(request: Request):
    t1 = timestamp()

    data = await request.json()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession()

    uid = request.state.session["uid"]

    db = await Database().init()
    table = db.get(table="Users")

    possible_find = await table.find_one(
        {"aminoId": {"$regex": regex_escape(data["aminoId"]), "$options": "i"}}
    )
    if possible_find:
        db.close()
        return Errors.AminoIdWasTaken()

    await table.update_one({"id": uid}, {"$set": {"aminoId": data["aminoId"]}})
    db.close()

    return Base.Answer(spent_time=timestamp() - t1)


@profile_methods.get("/g/s/user-profile/search")
@profile_methods.get("/x{ndcId}/s/user-profile/search")
async def user_search(
    request: Request,
    q: str = "",
    size: int = 25,
    pageToken: str | None = None,
    ndcId: int = 0,
):
    t1 = timestamp()
    
    q_stripped = q.strip()
    if q_stripped == "":
        return Base.Answer(
            {"userProfileList": [], "paging": {}, "userProfileCount": 0},
            spent_time=timestamp() - t1,
        )

    size = size if 0 < size < 101 else 25
    start = parse_page_token(pageToken, 0)

    try:
        db = await Database().init()
        g_users = db.get(table="Users")
        xndc_users = db.get(f"x{ndcId}", "Users")

        nickname_query = regex_escape(q_stripped)
        query = {"nickname": {"$regex": nickname_query, "$options": "i"}}

        users = [
            item
            async for item in xndc_users.find(query)
            .skip(start)
            .limit(size)
            .sort("timestamp", DESCENDING)
        ]

        seen = set()
        unique_users = []
        for item in users:
            if item["id"] not in seen:
                seen.add(item["id"])
                unique_users.append(item)

        userProfileList = []
        for item in unique_users:
            g_row = await g_users.find_one({"id": item["id"]})
            merged = (g_row or {}) | item
            userProfileList.append(User.GetUserInfo(merged, ndcId=ndcId))

        if userProfileList:
            return Base.Answer(
                {
                    "userProfileList": userProfileList,
                    "paging": calculate_page_tokens(start, size, userProfileList),
                    "userProfileCount": await xndc_users.count_documents(query),
                },
                spent_time=timestamp() - t1,
            )
        else:
            return Base.Answer(
                {"userProfileList": [], "paging": {}, "userProfileCount": 0},
                spent_time=timestamp() - t1,
            )
    finally:
        db.close()


@profile_methods.get("/g/s/user-profile/reminder-stat")
async def get_visits(request: Request):
    return Base.Answer({"visitorsCount": 0, "unreadVisitorsCount": 0})


@profile_methods.get("/g/s/account/affiliations")
async def affiliations_config(request: Request):
    if not request.state.session["validsession"]:
        return Errors.InvalidSession()

    trigger_uid = request.state.session["uid"]
    db = await Database().init()
    table = db.get(table="Users")

    info = await table.find_one({"id": trigger_uid})
    if info is None:
        return Errors.AccountNotExist()

    return Base.Answer({"affiliations": info.get("communityList", [])})


@profile_methods.get("/x{ndcId}/s/user-profile/recommended")
async def get_recommended_profiles(request: Request, ndcId: int):
    return Base.Answer({"userProfileList": []})


@profile_methods.get("/x{ndcId}/s/check-in/history")
async def check_in_history(request: Request, startTime: int, stopTime: int, ndcId: int, timezone: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)
    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    table = db.get(f"x{ndcId}", table="Users")
    row = await table.find_one({"id": trigger_uid})
    if row is None:
        db.close()
        return Errors.AccountNotExist(timestamp() - t1)
    db.close()

    start_dt = datetime.fromtimestamp(startTime / 1000, UTC) + timedelta(minutes=timezone)
    stop_dt = datetime.fromtimestamp(stopTime / 1000, UTC) + timedelta(minutes=timezone)
    start_str, stop_str = _date_str(start_dt), _date_str(stop_dt)

    full_history = row.get("checkInHistory", {}) or {}
    #history = full_history #{d: v for d, v in full_history.items() if start_str <= d <= stop_str}

    today_str = _date_str(_local_date(timezone))

    filtered = {d: v for d, v in full_history.items() if start_str <= d <= stop_str}

    return Base.Answer(
        {
            "checkInHistory": {
                "joinedTime": None,
                "startTime": startTime,
                "stopTime": stopTime,
                "consecutiveCheckInDays": row.get("consecutiveCheckInDays", 0),
                "hasCheckInToday": row.get("lastCheckInDate") == today_str,
                "hasAnyCheckIn": bool(full_history),
                "history": dumps(filtered),
            },
            "brokenStreaks": row.get("brokenStreaks", 0),
        },
        spent_time=timestamp() - t1,
    )


@profile_methods.get("/x{ndcId}/s/community/general-check")
@profile_methods.post("/x{ndcId}/s/community/general-check")
async def community_general_check(request: Request, ndcId: int):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)
    trigger_uid = request.state.session["uid"]

    #tz = await _get_tz(request)
    today_str = datetime.now().strftime("%Y-%m-%d") #_date_str(_local_date(tz))

    db = await Database().init()
    try:
        com_table = db.get(table="Communities")
        community = await com_table.find_one({"id": ndcId})
        if community is None:
            return Errors.DataNotExist(timestamp() - t1)

        table = db.get(f"x{ndcId}", table="Users")
        row = await table.find_one({"id": trigger_uid})
    finally:
        db.close()

    if row is None:
        return Errors.AccountNotExist(timestamp() - t1)

    if row.get("banned"):
        return Errors.UserBanned(timestamp() - t1)

    checked_in_today = row.get("lastCheckInDate") == today_str

    return Base.Answer(
        {
            "hasCheckInToday": checked_in_today,
            "consecutiveCheckInDays": int(row.get("consecutiveCheckInDays", 0)),
            "canPlayLottery": checked_in_today and row.get("lastLotteryDate") != today_str,
            "userProfile": User.GetUserInfo(row, ndcId=ndcId),
            "notificationsCount": 0,
            "noticesCount": 0,
            "hasPendingReviewRequest": False,
            "promotion": None,
            "communityMembershipRequestStatus": 0,
        },
        spent_time=timestamp() - t1,
    )

@profile_methods.get("/x{ndcId}/s/user-profile/{userId}/achievements")
async def get_user_achievements(request: Request, userId: str, ndcId: int):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    db = await Database().init()
    table = db.get(f"x{ndcId}", table="Users")
    row = await table.find_one({"id": userId})
    if row is None:
        db.close()
        return Errors.AccountNotExist(timestamp() - t1)

    blogs_table = db.get(f"x{ndcId}", table="Blogs")
    blogs_count = await blogs_table.count_documents({"authorId": userId, "status": 0})
    db.close()
    return Base.Answer(
        {
            "achievements": {
                "secondsSpent": int(row.get("secondsSpent", 0)),
                "numberOfFollowersCount": len(row.get("whoFollows", [])),
                "numberOfPostsCreated": blogs_count,
            }
        },
        spent_time=timestamp() - t1,
    )


@profile_methods.get("/g/s/user-profile/{uid}/joined")
@profile_methods.get("/x{ndcId}/s/user-profile/{uid}/joined")
async def get_user_following(
    uid: str, request: Request, ndcId: int = 0, start: int = 0, size: int = 25
):
    t1 = timestamp()

    db = await Database().init()
    xndcid_table = db.get(f"x{ndcId}", "Users")
    row = await xndcid_table.find_one({"id": uid})
    following = row["following"][start : start + size]
    following_list = [
        User.GetUserInfo(
            await xndcid_table.find_one({"id": item}),
            ndcId=ndcId,
        )
        for item in following
    ]

    db.close()
    return Base.Answer({"userProfileList": following_list}, spent_time=timestamp() - t1)


@profile_methods.get("/g/s/user-profile/{uid}/member")
@profile_methods.get("/x{ndcId}/s/user-profile/{uid}/member")
async def get_user_followers(
    uid: str, request: Request, ndcId: int = 0, start: int = 0, size: int = 25
):
    t1 = timestamp()

    db = await Database().init()
    xndcid_table = db.get(f"x{ndcId}", "Users")
    row = await xndcid_table.find_one({"id": uid})
    followers = row["whoFollows"][start : start + size]
    followers_list = [
        User.GetUserInfo(
            await xndcid_table.find_one({"id": item}),
            ndcId=ndcId,
        )
        for item in followers
    ]

    db.close()
    return Base.Answer({"userProfileList": followers_list}, spent_time=timestamp() - t1)


@profile_methods.get("/g/s/user-profile/{uid}/g-comment")
@profile_methods.get("/x{ndcId}/s/user-profile/{uid}/comment")
async def get_user_wall(
    uid: str,
    request: Request,
    ndcId: int = 0,
    start: int = 0,
    size: int = 25,
    sort: str = "newest",
):
    t1 = timestamp()

    trigger_uid = request.state.session.get("uid")

    def listed(result: dict):
        return list(result.items())

    db = await Database().init()
    xndcid_table = db.get(f"x{ndcId}", "Users")
    row = await xndcid_table.find_one({"id": uid})
    if row is None:
        db.close()
        return Errors.AccountNotExist(timestamp() - t1)

    wall_data = row.get("wall", {})

    if sort == "newest":
        all_wall_comments = listed(wall_data)
        all_wall_comments.reverse()
    elif sort == "vote":
        all_wall_comments = sorted(
            listed(wall_data), key=lambda d: len(d[1]["upvotes"]), reverse=True
        )
    else:
        all_wall_comments = listed(wall_data)

    wall_comments = []
    for _comment_id, _comment_info in all_wall_comments:
        if _comment_info["isSubWM"] is False:
            wall_comments.append((_comment_id, _comment_info))

    wall_comments = wall_comments[start : start + size]
    wc_list = [
        await Comments.Parent(
            item[1], item[0], uid, xndcid_table, trigger_uid, ndcId=ndcId
        )
        for item in wall_comments
    ]

    db.close()
    return Base.Answer({"commentList": wc_list}, spent_time=timestamp() - t1)


@profile_methods.get("/g/s/user-profile/{uid}/g-comment/{commentId}")
@profile_methods.get("/g/s/user-profile/{uid}/g-comment/{commentId}/response")
@profile_methods.get("/x{ndcId}/s/user-profile/{uid}/comment/{commentId}")
@profile_methods.get("/x{ndcId}/s/user-profile/{uid}/comment/{commentId}/response")
async def get_user_wall_answers(uid: str, commentId: str, request: Request, ndcId: int = 0):
    t1 = timestamp()

    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    xndcid_table = db.get(f"x{ndcId}", "Users")
    row = await xndcid_table.find_one({"id": uid})
    if row is None:
        db.close()
        return Errors.AccountNotExist(timestamp() - t1)

    all_wall = row.get("wall", {})
    if commentId not in all_wall:
        db.close()
        return Errors.NotFound(timestamp() - t1)

    comment_thread = all_wall[commentId].get("subWMs", [])
    certain_wall = []
    for _comment_id, _comment_info in all_wall.items():
        if _comment_id in comment_thread:
            certain_wall.append((_comment_id, _comment_info))

    wc_list = [
        await Comments.Son(
            item[1],
            item[0],
            commentId,
            uid,
            xndcid_table,
            trigger_uid,
            ndcId=ndcId,
        )
        for item in certain_wall
    ]

    db.close()
    return Base.Answer({"commentList": wc_list}, spent_time=timestamp() - t1)


@profile_methods.delete("/g/s/user-profile/{uid}/comment/{commentId}")
@profile_methods.delete("/g/s/user-profile/{uid}/g-comment/{commentId}")
@profile_methods.delete("/x{ndcId}/s/user-profile/{uid}/comment/{commentId}")
async def delete_post_from_wall(
    request: Request, uid: str, commentId: str, ndcId: int = 0
):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    if uid == trigger_uid:
        db = await Database().init()
        table = db.get(f"x{ndcId}", "Users")
        user_info = await table.find_one({"id": uid})

        if user_info is None:
            db.close()
            return Errors.AccountNotExist(timestamp() - t1)

        wall = user_info.get("wall", {})
        if wall.get(commentId):
            unset_fields = {f"wall.{commentId}": ""}
            comment_to_delete = wall[commentId]

            if comment_to_delete.get("isSubWM") is False:
                sub_wms = comment_to_delete.get("subWMs", [])
                for key in sub_wms:
                    if key in wall.keys():
                        unset_fields[f"wall.{key}"] = ""
            else:
                parent_comment_id = None
                for parent_id, parent_comment_info in wall.items():
                    if commentId in parent_comment_info.get("subWMs", []):
                        parent_comment_id = parent_id
                        break

                if parent_comment_id:
                    await table.update_one(
                        {"id": uid},
                        {"$pull": {f"wall.{parent_comment_id}.subWMs": commentId}},
                    )

            await table.update_one({"id": uid}, {"$unset": unset_fields})

        db.close()
    return Base.Answer(spent_time=timestamp() - t1)


@profile_methods.post("/g/s/user-profile/{uid}/comment")
@profile_methods.post("/g/s/user-profile/{uid}/g-comment")
@profile_methods.post("/x{ndcId}/s/user-profile/{uid}/comment")
@turtlelimiter(limit=1, period=TurtleTime.second, tag="blog-comment")
async def post_on_user_wall(
    uid: str,
    request: Request,
    ndcId: int = 0,
    start: int = 0,
    size: int = 25,
    sort: str = "newest",
):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    data = await request.json()
    try:
        if not data["content"]:
            raise Exception()
    except Exception:
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()
    xndcid_table = db.get(f"x{ndcId}", "Users")

    commentUid = str(uuid4())
    wm = ModelFabric.Construct(
        Community.WallMessage,
        authorId=trigger_uid,
        content=data["content"],
        mediaList=data.get("mediaList", []),
        isSubWM=True if data.get("respondTo") else False,
    )

    if data.get("respondTo"):
        await xndcid_table.update_one(
            {"id": uid}, {"$push": {f"wall.{data['respondTo']}.subWMs": commentUid}}
        )
        commentObj = await Comments.Son(
            wm,
            commentUid,
            data["respondTo"],
            uid,
            xndcid_table,
            trigger_uid,
            ndcId=ndcId,
        )
    else:
        commentObj = await Comments.Parent(
            wm, commentUid, uid, xndcid_table, trigger_uid, ndcId=ndcId
        )

    await xndcid_table.update_one({"id": uid}, {"$set": {f"wall.{commentUid}": wm}})

    db.close()
    return Base.Answer({"comment": commentObj}, spent_time=timestamp() - t1)


@profile_methods.post("/g/s/user-profile/{uid}/comment/{commentId}/vote")
@profile_methods.post("/g/s/user-profile/{uid}/g-comment/{commentId}/vote")
@profile_methods.post("/x{ndcId}/s/user-profile/{uid}/comment/{commentId}/vote")
async def vote_comment(request: Request, uid: str, commentId: str, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]
    try:
        data = await request.json()
    except Exception:
        data = {}

    value = data.get("value", 0)
    db = await Database().init()
    table = db.get(f"x{ndcId}", "Users")
    user_info = await table.find_one({"id": uid})
    if user_info is None:
        db.close()
        return Errors.InvalidLogin(timestamp() - t1)

    if commentId not in user_info.get("wall", {}):
        db.close()
        return Errors.DataNotExist(timestamp() - t1)

    if value == 1:
        await table.update_one(
            {"id": uid},
            {
                "$addToSet": {f"wall.{commentId}.upvotes": trigger_uid},
                "$pull": {f"wall.{commentId}.downvotes": trigger_uid},
            },
        )
    elif value == -1:
        await table.update_one(
            {"id": uid},
            {
                "$addToSet": {f"wall.{commentId}.downvotes": trigger_uid},
                "$pull": {f"wall.{commentId}.upvotes": trigger_uid},
            },
        )
    else:
        db.close()
        return Errors.InvalidRequest()

    db.close()
    return Base.Answer(spent_time=timestamp() - t1)


@profile_methods.delete("/g/s/user-profile/{uid}/comment/{commentId}/vote")
@profile_methods.delete("/g/s/user-profile/{uid}/g-comment/{commentId}/vote")
@profile_methods.delete("/x{ndcId}/s/user-profile/{uid}/comment/{commentId}/vote")
async def remove_comment_vote(
    request: Request, uid: str, commentId: str, ndcId: int = 0
):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]
    db = await Database().init()
    table = db.get(f"x{ndcId}", "Users")

    user_info = await table.find_one({"id": uid})
    if user_info is None:
        db.close()
        return Errors.AccountNotExist(timestamp() - t1)

    if commentId not in user_info.get("wall", {}):
        db.close()
        return Errors.NotFound(timestamp() - t1)

    await table.update_one(
        {"id": uid},
        {
            "$pull": {
                f"wall.{commentId}.upvotes": trigger_uid,
                f"wall.{commentId}.downvotes": trigger_uid,
            }
        },
    )

    db.close()
    return Base.Answer(spent_time=timestamp() - t1)


@profile_methods.get("/g/s/user-profile/{uid}/comment/{commentId}/vote")
@profile_methods.get("/g/s/user-profile/{uid}/g-comment/{commentId}/vote")
@profile_methods.get("/x{ndcId}/s/user-profile/{uid}/comment/{commentId}/vote")
async def get_comment_voted_users(
    request: Request,
    uid: str,
    commentId: str,
    ndcId: int = 0,
    pageToken: str | None = None,
    start: int = 0,
    size: int = 25,
):
    t1 = timestamp()

    db = await Database().init()
    xndcid_table = db.get(f"x{ndcId}", "Users")
    row = await xndcid_table.find_one({"id": uid})
    if row is None:
        return Base.Answer({"userProfileList": []}, spent_time=timestamp() - t1)

    try:
        comment = row["wall"][commentId]
        votes = comment.get("upvotes", []) + comment.get("downvotes", [])
        votes_selected = votes[start : start + size]
    except Exception:
        db.close()
        return Base.Answer({"userProfileList": []}, spent_time=timestamp() - t1)

    voters_list = [
        User.GetUserInfo(
            await xndcid_table.find_one({"id": item}),
            ndcId=ndcId,
        )
        for item in votes_selected
    ]

    db.close()
    return Base.Answer({"userProfileList": voters_list}, spent_time=timestamp() - t1)


@profile_methods.post("/g/s/user-profile/{uid}/member")
@profile_methods.post("/x{ndcId}/s/user-profile/{uid}/member")
async def follow_user(uid: str, request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    suid = request.state.session["uid"]
    if suid == uid:
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()
    table = db.get(f"x{ndcId}", "Users")
    target_user = await table.find_one({"id": uid})
    inited_user = await table.find_one({"id": suid})
    if suid not in target_user["whoFollows"] or uid not in inited_user["following"]:
        await table.update_one({"id": uid}, {"$push": {"whoFollows": suid}})
        await table.update_one({"id": suid}, {"$push": {"following": uid}})

    db.close()
    return Base.Answer(spent_time=timestamp() - t1)


@profile_methods.delete("/g/s/user-profile/{uid}/member/{inited_uid}")
@profile_methods.delete("/x{ndcId}/s/user-profile/{uid}/member/{inited_uid}")
async def unfollow_user(uid: str, request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    suid = request.state.session["uid"]
    if suid == uid:
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()
    table = db.get(f"x{ndcId}", "Users")
    await table.update_one({"id": uid}, {"$pull": {"whoFollows": suid}})
    await table.update_one({"id": suid}, {"$pull": {"following": uid}})

    db.close()
    return Base.Answer(spent_time=timestamp() - t1)



@profile_methods.get("/g/s/user-profile/{uid}")
@profile_methods.get("/x{ndcId}/s/user-profile/{uid}")
async def get_user_info(uid: str, request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)
    trigger_uid = request.state.session["uid"]
    db = await Database().init()
    g_table = db.get(table="Users")
    table = db.get(database=f"x{ndcId}", table="Users")
    row2 = await table.find_one({"id": uid})
    if row2 is None:
        return Errors.AccountNotExist(timestamp() - t1)

    global_row = await g_table.find_one({"id": uid})
    if global_row:
        if not row2.get("tagList"):
            global_tag_list = global_row.get("tagList")
            if global_tag_list:
                row2["tagList"] = global_tag_list

        if "isTeamMember" in global_row:
            row2["isTeamMember"] = global_row["isTeamMember"]

        if "isVerified" in global_row:
            row2["isVerified"] = global_row["isVerified"]
        if global_row.get("status", 0) in [9, 10]:
            row2["status"] = global_row["status"]
        if global_row.get("extensions", {}).get("__disabledLevel__"):
            row2["extensions"]["__disabledLevel__"] = global_row["extensions"]["__disabledLevel__"]

        if ndcId == 0:
            row2 = global_row | row2
        
    db.close()
    return Base.Answer(
        {"userProfile": User.GetUserInfo(row2, triggerUserId=trigger_uid, extensions=row2.get("extensions"), ndcId=ndcId)},
        spent_time=timestamp() - t1,
    )



@profile_methods.post("/g/s/user-profile/{uid}")
@profile_methods.post("/x{ndcId}/s/user-profile/{uid}")
@profile_methods.post("/g/s/account/{uid}")
@profile_methods.post("/x{ndcId}/s/account/{uid}")
async def edit_user_info(uid, request: Request, ndcId=0):
	t1 = timestamp()
	data = await request.json()

	print(f"editing profile {uid}:", data)
	lang = None

	if not request.state.session["validsession"]:
		return Errors.InvalidSession(timestamp() - t1)

	trigger_uid = request.state.session["uid"]
	if trigger_uid != uid:
		return Errors.InvalidRequest(timestamp() - t1)

	preparedQueries = {"modifiedTime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}

	if isinstance(data.get("nickname"), str):
		if len(data["nickname"].strip()) == 0:
			return Errors.InvalidRequest(timestamp() - t1)
		preparedQueries.update({"nickname": data["nickname"]})

	if isinstance(data.get("content"), str):
		preparedQueries.update({"description": data["content"]})

	if isinstance(data.get("icon"), str):
		if data["icon"].startswith("https://media.altamino.top/"):
			preparedQueries.update({"icon": data["icon"]})

	if data.get("mediaList"):
		mediaList = [item[1] for item in data["mediaList"]]
		preparedQueries.update({"mediaList": mediaList})

	if data.get("extensions"):
		extensions = data["extensions"]
		if isinstance(extensions.get("defaultBubbleId"), str):
			pass  # [TODO]: implement default bubble id
		if extensions.get("contentLanguage", "en") in ["ru", "en", "ar", "es"]:
			lang = {"lang": extensions.get("contentLanguage", "en")}
		if extensions.get("style"):
			style = extensions["style"]

			# background!
			preparedQueries.update({"backgroundColor": style.get("backgroundColor")})
			if isinstance(style.get("backgroundMediaList"), list):
				mediaList = [item[1] for item in style["backgroundMediaList"]]
				preparedQueries.update({"backgroundMediaList": mediaList})
			else:
				preparedQueries.update({"backgroundMediaList": None})

	if len(preparedQueries) == 0 and lang is None:
		return Base.Answer({"exceptions": "No data provided."})

	db = await Database().init()

	if preparedQueries:
		table = db.get(database=f"x{ndcId}", table="Users")
		await table.update_one({"id": uid}, {"$set": preparedQueries})

	if lang:
		table = db.get(table="Users")
		await table.update_one({"id": uid}, {"$set": lang})

	table = db.get(database=f"x{ndcId}", table="Users")
	row2 = await table.find_one({"id": uid})

	db.close()

	if row2 is None:
		return Errors.AccountNotExist(timestamp() - t1)

	return Base.Answer(
		{"userProfile": User.GetUserInfo(row2, ndcId=ndcId)},
		spent_time=timestamp() - t1,
	)



@profile_methods.get("/g/s/account")
@profile_methods.get("/x{ndcId}/s/account")
async def get_self_info(request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    uid = request.state.session["uid"]

    db = await Database().init()
    table = db.get(table="Users")
    row1 = await table.find_one({"id": uid})
    if row1 is None:
        return Errors.AccountNotExist(timestamp() - t1)
    table = db.get(database=f"x{ndcId}", table="Users")
    row2 = await table.find_one({"id": uid})
    if row2 is None:
        return Errors.AccountNotExist(timestamp() - t1)
    db.close()
    return Base.Answer(
        {"userProfile": User.GetUserInfo(row1 | row2, ndcId=ndcId)},
        spent_time=timestamp() - t1,
    )


@profile_methods.get("/g/s/wallet")
@profile_methods.get("/x{ndcId}/s/wallet")
async def get_wallet_info(request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    table = db.get(table="Users")
    await settle_user_active_coins(db, trigger_uid)
    row = await table.find_one({"id": trigger_uid})
    if row is None:
        db.close()
        return Errors.AccountNotExist(timestamp() - t1)
    db.close()
    current_coins = round(float(row.get("coins", 0.0)), 2)
    return Base.Answer(
        {
            "wallet": {
                "businessCoinsEnabled": False,
                "newUserCoupon": None,
                "adsFlags": 2147483647,
                "adsVideoStats": {
                    "canWatchVideo": False,
                    "canEarnedCoins": 0,
                    "canNotWatchVideoReason": None,
                    "watchVideoMaxCount": 0,
                    "nextWatchVideoInterval": 0,
                    "watchedVideoCount": 0,
                },
                "totalCoins": int(current_coins),
                "totalCoinsFloat": current_coins,
                "adsEnabled": False,
                "totalBusinessCoins": 0,
                "totalBusinessCoinsFloat": 0,
            }
        },
        spent_time=timestamp() - t1,
    )

@profile_methods.post("/g/s/wallet/daily-reward")
@profile_methods.post("/x{ndcId}/s/check-in")
async def claim_daily_reward(request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)
    trigger_uid = request.state.session["uid"]

    tz = await _get_tz(request)
    now_local = _local_date(tz)
    today_str = _date_str(now_local)
    yesterday_str = _date_str(now_local - timedelta(days=1))

    db = await Database().init()
    try:
        table = db.get(f"x{ndcId}", table="Users")
        global_table = db.get(table="Users")

        row = await table.find_one({"id": trigger_uid})
        if row is None:
            return Errors.AccountNotExist(timestamp() - t1)

        if row.get("lastCheckInDate") == today_str:
            return Errors.AlreadyClaimed(timestamp() - t1)

        prev_streak = int(row.get("consecutiveCheckInDays", 0))
        if row.get("lastCheckInDate") == yesterday_str:
            streak = prev_streak + 1
            broke = 0
        else:
            streak = 1
            broke = 1 if row.get("lastCheckInDate") else 0

        coins = round(random.choices(CHECKIN_COIN_REWARDS, CHECKIN_COIN_WEIGHTS, k=1)[0], 2)
        rep = _earned_rep(streak)


        result = await table.update_one(
            {"id": trigger_uid, "lastCheckInDate": {"$ne": today_str}},
            {
                "$inc": {"reputation": rep, "brokenStreaks": broke},
                "$set": {
                    "lastCheckInDate": today_str,
                    "consecutiveCheckInDays": streak,
                    f"checkInHistory.{today_str}": 1,
                },
            },
        )
        if result.modified_count == 0:
            return Errors.AlreadyClaimed(timestamp() - t1)

        # Монеты — глобальный баланс.
        await global_table.update_one(
            {"id": trigger_uid},
            {"$inc": {"coins": coins}},
        )

        updated_row = await table.find_one({"id": trigger_uid})
        global_row = await global_table.find_one({"id": trigger_uid})
    finally:
        db.close()

    updated_coins = round(float((global_row or {}).get("coins", 0.0)), 2)
    return Base.Answer(
        {
            "claimedCoins": coins,
            "totalCoins": int(updated_coins),
            "totalCoinsFloat": updated_coins,
            "consecutiveCheckInDays": streak,
            "canPlayLottery": updated_row.get("lastLotteryDate") != today_str,
            "earnedReputationPoint": rep,
            "additionalReputationPoint": 0,
            "checkInHistory": {
                "joinedTime": None,
                "startTime": None,
                "stopTime": None,
                "consecutiveCheckInDays": streak,
                "hasCheckInToday": True,
                "hasAnyCheckIn": True,
                "history": None,
            },
            "userProfile": User.GetUserInfo(updated_row, ndcId=ndcId),
        },
        spent_time=timestamp() - t1,
    )

@profile_methods.post("/g/s/check-in/lottery")
@profile_methods.post("/x{ndcId}/s/check-in/lottery")
async def claim_daily_lottery(request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)
    trigger_uid = request.state.session["uid"]

    tz = await _get_tz(request)
    today_str = _date_str(_local_date(tz))

    db = await Database().init()
    try:
        table = db.get(f"x{ndcId}", table="Users")
        global_table = db.get(table="Users")

        row = await table.find_one({"id": trigger_uid})
        if row is None:
            return Errors.AccountNotExist(timestamp() - t1)

        if row.get("lastCheckInDate") != today_str:
            return Errors.LotteryNotAvailable(timestamp() - t1)

        if row.get("lastLotteryDate") == today_str:
            return Errors.LotteryPlayed(timestamp() - t1)

        award = round(random.choices(LOTTERY_REWARDS, LOTTERY_WEIGHTS, k=1)[0], 2)

        result = await table.update_one(
            {"id": trigger_uid, "lastLotteryDate": {"$ne": today_str}},
            {"$set": {"lastLotteryDate": today_str}},
        )
        if result.modified_count == 0:
            return Errors.LotteryPlayed(timestamp() - t1)

        await global_table.update_one(
            {"id": trigger_uid},
            {"$inc": {"coins": award}},
        )

        updated_row = await table.find_one({"id": trigger_uid})
    finally:
        db.close()

    return Base.Answer(
        {
            "lotteryLog": {
                "awardValue": int(award),
                "awardType": 1,
                "parentId": None,
                "parentType": 0,
                "objectId": str(uuid4()),
                "objectType": 0,
                "createdTime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "refObject": None,
            },
            "userProfile": User.GetUserInfo(updated_row, ndcId=ndcId),
        },
        spent_time=timestamp() - t1,
    )


@profile_methods.get("/g/s/wallet/setting/ads")
async def get_wallet_ads_info(request: Request):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    table = db.get(table="Users")
    row = await table.find_one({"id": trigger_uid})
    if row is None:
        return Errors.AccountNotExist(timestamp() - t1)
    db.close()
    return Base.Answer(
        {"estimatedCoinsEarnedByAds": 0, "coinsEarnedByAds": {"total": 0, "weekly": 0}},
        spent_time=timestamp() - t1,
    )