from datetime import UTC, datetime
from re import escape as regex_escape
from time import time as timestamp
from typing import Union
from uuid import uuid4

from fastapi import APIRouter, Request
from pymongo import DESCENDING

from helpers.database.models import Community, ModelFabric
from helpers.database.mongo import Database
from helpers.decorators.turtlelimit import TurtleTime, turtlelimiter
from helpers.functions import calculate_page_tokens, parse_page_token
from helpers.routers.cachable import CachableRoute
from objects import Base, Blog, Comments, Errors, User

blog_methods = APIRouter()
blog_methods.route_class = CachableRoute


@blog_methods.get("/x{ndcId}/s/feed/blog-recommended")
async def get_recommended_blogs(request: Request, ndcId: int):
    # mock for now
    return Base.Answer({"blogList": []})


@blog_methods.get("/x{ndcId}/s/feed/blog-all")
@blog_methods.get("/g/s/feed/blog-all")
async def get_latest_blog_posts(
    request: Request,
    ndcId: int = 0,
    pageToken: str | None = None,
    start: int = 0,
    size: int = 5,
    q: Union[str, None] = None,
):
    t1 = timestamp()
    size = size if 0 < size < 101 else 25
    start = parse_page_token(pageToken, start)

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")

    query = {}
    if q:
        query["title"] = {"$regex": regex_escape(q), "$options": "i"}

    blogs = [
        item
        async for item in table.find(query)
        .skip(start)
        .limit(size)
        .sort("createdTime", DESCENDING)
    ]

    blogList = [
        await Blog.Info(
            item, db, ndcId=ndcId, trigger_uid=request.state.session.get("uid")
        )
        for item in blogs
    ]

    await db.close()
    return Base.Answer(
        {
            "blogList": blogList,
            "paging": calculate_page_tokens(start, size, blogList),
        },
        spent_time=timestamp() - t1,
    )


@blog_methods.get("/g/s/blog")
@blog_methods.get("/x{ndcId}/s/blog")
async def get_blogs(
    request: Request,
    q: Union[str, None] = None,
    ndcId: int = 0,
    size: int = 25,
    pageToken: str | None = None,
    start: int = 0,
):
    t1 = timestamp()
    size = size if 0 < size < 101 else 25
    start = parse_page_token(pageToken, start)

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")

    query = {"blogType": 0}
    if q:
        query["title"] = {"$regex": regex_escape(q), "$options": "i"}

    blogs = [
        item
        async for item in table.find(query)
        .skip(start)
        .limit(size)
        .sort("createdTime", DESCENDING)
    ]

    blogList = [
        await Blog.Info(
            item, db, ndcId=ndcId, trigger_uid=request.state.session.get("uid")
        )
        for item in blogs
    ]

    await db.close()
    return Base.Answer(
        {
            "blogList": blogList,
            "paging": calculate_page_tokens(start, size, blogList),
        },
        spent_time=timestamp() - t1,
    )


@blog_methods.get("/g/s/blog/{blogId}")
@blog_methods.get("/x{ndcId}/s/blog/{blogId}")
async def get_blog(
    request: Request,
    blogId: str,
    ndcId: int = 0,
):
    t1 = timestamp()

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")

    blog = await table.find_one({"id": blogId})
    if blog:
        blog_info = await Blog.Info(
            blog, db, ndcId=ndcId, trigger_uid=request.state.session.get("uid")
        )
        await db.close()

        return Base.Answer(
            {"blog": blog_info},
            spent_time=timestamp() - t1,
        )

    await db.close()
    return Errors.DataNotExist(timestamp() - t1)


# get blog's wall


@blog_methods.get("/g/s/blog/{blogId}/comment")
@blog_methods.get("/x{ndcId}/s/blog/{blogId}/comment")
async def get_blog_comments(
    request: Request,
    blogId: str,
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
    table = await db.get(f"x{ndcId}", "Blogs")
    blog_info = await table.find_one({"id": blogId})
    if blog_info is None:
        await db.close()
        return Errors.DataNotExist(timestamp() - t1)

    wall_data = blog_info.get("wall", {})

    if sort == "newest":
        wall = listed(wall_data)
        wall.reverse()
    elif sort == "vote":
        wall = sorted(
            listed(wall_data), key=lambda d: len(d[1]["upvotes"]), reverse=True
        )
    else:  # oldest and other
        wall = listed(wall_data)

    wall_chunk = []
    for _item_id, _item_info in wall:
        if _item_info["isSubWM"] is False:
            wall_chunk.append((_item_id, _item_info))

    xndc_users = await db.get(f"x{ndcId}", "Users")
    wall_chunk = wall_chunk[start : start + size]
    wc_list = [
        await Comments.Parent(
            item[1], item[0], blogId, xndc_users, trigger_uid, ndcId=ndcId, parentType=2
        )
        for item in wall_chunk
    ]

    await db.close()
    return Base.Answer({"commentList": wc_list}, spent_time=timestamp() - t1)


# get replies to blog's wall post


@blog_methods.get("/g/s/blog/{blogId}/comment/{commentId}")
@blog_methods.get("/g/s/blog/{blogId}/comment/{commentId}/response")
@blog_methods.get("/x{ndcId}/s/blog/{blogId}/comment/{commentId}")
@blog_methods.get("/x{ndcId}/s/blog/{blogId}/comment/{commentId}/response")
async def get_blog_comment_answers(
    request: Request,
    blogId: str,
    commentId: str,
    ndcId: int = 0,
    start: int = 0,
    size: int = 25,
):
    t1 = timestamp()

    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")
    blog_info = await table.find_one({"id": blogId})
    if blog_info is None:
        await db.close()
        return Errors.DataNotExist(timestamp() - t1)

    wall_data = blog_info.get("wall", {})
    if commentId not in wall_data:
        await db.close()
        return Errors.DataNotExist(timestamp() - t1)

    wall_thread = wall_data[commentId].get("subWMs", [])
    certain_wall = []
    for _item_id, _item_info in wall_data.items():
        if _item_id in wall_thread:
            certain_wall.append((_item_id, _item_info))

    xndc_users = await db.get(f"x{ndcId}", "Users")
    certain_wall = certain_wall[start : start + size]
    wc_list = [
        await Comments.Son(
            item[1],
            item[0],
            commentId,
            blogId,
            xndc_users,
            trigger_uid,
            ndcId=ndcId,
            parentType=2,
        )
        for item in certain_wall
    ]

    await db.close()
    return Base.Answer({"commentList": wc_list}, spent_time=timestamp() - t1)


# post on blog's wall


@blog_methods.post("/g/s/blog/{blogId}/comment")
@blog_methods.post("/g/s/item/{blogId}/comment")
@blog_methods.post("/x{ndcId}/s/blog/{blogId}/comment")
@blog_methods.post("/x{ndcId}/s/item/{blogId}/comment")
@turtlelimiter(limit=1, period=TurtleTime.second, tag="blog-comment")
async def post_blog_comment(
    blogId: str,
    request: Request,
    ndcId: int = 0,
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
    table = await db.get(f"x{ndcId}", "Blogs")
    blog_info = await table.find_one({"id": blogId})
    if not blog_info:
        await db.close()
        return Errors.DataNotExist(timestamp() - t1)

    commentUid = str(uuid4())
    wm = ModelFabric.Construct(
        Community.WallMessage,
        authorId=trigger_uid,
        content=data["content"],
        mediaList=data.get("mediaList", []),
        isSubWM=True if data.get("respondTo") else False,
    )

    xndc_users = await db.get(f"x{ndcId}", "Users")
    if data.get("respondTo"):
        await table.update_one(
            {"id": blogId},
            {"$push": {f"wall.{data['respondTo']}.subWMs": commentUid}},
        )
        wmObj = await Comments.Son(
            wm,
            commentUid,
            data["respondTo"],
            blogId,
            xndc_users,
            trigger_uid,
            ndcId=ndcId,
            parentType=2,
        )
    else:
        wmObj = await Comments.Parent(
            wm, commentUid, blogId, xndc_users, trigger_uid, ndcId=ndcId, parentType=2
        )

    await table.update_one({"id": blogId}, {"$set": {f"wall.{commentUid}": wm}})

    await db.close()
    return Base.Answer({"comment": wmObj}, spent_time=timestamp() - t1)


# edit blog post


@blog_methods.post("/g/s/blog/{blogId}")
@blog_methods.post("/x{ndcId}/s/blog/{blogId}")
async def edit_blog(request: Request, blogId: str, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]
    data = await request.json()

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")

    blog = await table.find_one({"id": blogId})
    if not blog:
        await db.close()
        return Errors.DataNotExist(timestamp() - t1)

    if blog["authorId"] != trigger_uid:
        await db.close()
        return Errors.NotEnoughRights(timestamp() - t1)

    preparedQueries = {"modifiedTime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}

    if "title" in data:
        preparedQueries["title"] = data["title"]
    if "content" in data:
        preparedQueries["content"] = data["content"]
    if "mediaList" in data:
        preparedQueries["mediaList"] = data["mediaList"]

    extensions = data.get("extensions", {})
    if extensions:
        current_extensions = blog.get("extensions", {})
        style = extensions.get("style", {})
        if style:
            current_style = current_extensions.get("style", {})
            for k in [
                "backgroundMediaList",
                "backgroundColor",
                "coverMediaIndexList",
                "coverMediaList",
            ]:
                if k in style:
                    current_style[k] = style[k]
            current_extensions["style"] = current_style

        if "privilegeOfCommentOnPost" in extensions:
            current_extensions["commentAllowance"] = extensions[
                "privilegeOfCommentOnPost"
            ]

        preparedQueries["extensions"] = current_extensions

    await table.update_one({"id": blogId}, {"$set": preparedQueries})
    updated_blog = await table.find_one({"id": blogId})
    blog_info = await Blog.Info(updated_blog, db, ndcId=ndcId, trigger_uid=trigger_uid)

    await db.close()
    return Base.Answer({"blog": blog_info}, spent_time=timestamp() - t1)


# delete blog post


@blog_methods.delete("/g/s/blog/{blogId}")
@blog_methods.delete("/x{ndcId}/s/blog/{blogId}")
async def delete_blog(request: Request, blogId: str, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")

    blog = await table.find_one({"id": blogId})
    if not blog:
        await db.close()
        return Errors.DataNotExist(timestamp() - t1)

    if blog["authorId"] != trigger_uid:
        await db.close()
        return Errors.NotEnoughRights(timestamp() - t1)

    await table.delete_one({"id": blogId})

    await db.close()
    return Base.Answer({}, spent_time=timestamp() - t1)


# add vote to blog


@blog_methods.post("/g/s/blog/{blogId}/vote")
@blog_methods.post("/g/s/item/{blogId}/vote")
@blog_methods.post("/x{ndcId}/s/blog/{blogId}/vote")
@blog_methods.post("/x{ndcId}/s/item/{blogId}/vote")
async def vote_blog(request: Request, blogId: str, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]
    try:
        data = await request.json()
    except Exception:
        data = {}
    value = data.get("value", 4)

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")

    # upvote
    if value in [1, 2, 3, 4]:
        await table.update_one(
            {"id": blogId},
            {
                "$addToSet": {"upvote": trigger_uid},
                "$pull": {"downvote": trigger_uid},
            },
        )
    # downvote
    elif value == -1:
        await table.update_one(
            {"id": blogId},
            {
                "$addToSet": {"downvote": trigger_uid},
                "$pull": {"upvote": trigger_uid},
            },
        )

    await db.close()
    return Base.Answer(spent_time=timestamp() - t1)


# remove vote from blog


@blog_methods.delete("/g/s/blog/{blogId}/vote")
@blog_methods.delete("/g/s/item/{blogId}/vote")
@blog_methods.delete("/x{ndcId}/s/blog/{blogId}/vote")
@blog_methods.delete("/x{ndcId}/s/item/{blogId}/vote")
async def remove_vote_from_blog(request: Request, blogId: str, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")

    await table.update_one(
        {"id": blogId}, {"$pull": {"upvote": trigger_uid, "downvote": trigger_uid}}
    )

    await db.close()
    return Base.Answer(spent_time=timestamp() - t1)


# see who voted for blog


@blog_methods.get("/g/s/blog/{blogId}/vote")
@blog_methods.get("/g/s/item/{blogId}/vote")
@blog_methods.get("/x{ndcId}/s/blog/{blogId}/vote")
@blog_methods.get("/x{ndcId}/s/item/{blogId}/vote")
async def get_blog_voters(
    request: Request,
    blogId: str,
    ndcId: int = 0,
    start: int = 0,
    size: int = 25,
):
    t1 = timestamp()

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")
    blog = await table.find_one({"id": blogId})
    if blog is None:
        await db.close()
        return Base.Answer({"userProfileList": []}, spent_time=timestamp() - t1)

    votes = blog.get("upvote", []) + blog.get("downvote", [])
    votes_selected = votes[start : start + size]

    xndc_users = await db.get(f"x{ndcId}", "Users")
    trigger_uid = request.state.session.get("uid")
    voters_list = [
        User.GetUserInfo(u, ndcId=ndcId, triggerUserId=trigger_uid)
        for item in votes_selected
        if (u := await xndc_users.find_one({"id": item}))
    ]

    await db.close()
    return Base.Answer({"userProfileList": voters_list}, spent_time=timestamp() - t1)


# post blog


@blog_methods.post("/g/s/blog")
@blog_methods.post("/x{ndcId}/s/blog")
@turtlelimiter(limit=1, period=TurtleTime.second, tag="post-blog")
async def post_blog(request: Request, ndcId: int = 0):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    data = await request.json()
    try:
        blog_type = data["type"]
        title = data["title"]
        content = data["content"]
        extensions = data.get("extensions", {})
    except KeyError:
        return Errors.InvalidRequest(timestamp() - t1)

    if blog_type not in [0, 3, 7]:
        return Errors.InvalidRequest(timestamp() - t1)

    db = await Database().init()

    if ndcId > 0:
        xndcid_users = await db.get(f"x{ndcId}", "Users")
        user_in_community = await xndcid_users.find_one({"id": trigger_uid})
        if not user_in_community:
            await db.close()
            return Errors.NotEnoughRights(timestamp() - t1)
    else:
        return Errors.NotEnoughRights(timestamp() - t1)

    style = extensions.get("style", {})
    useful_extensions = {
        "commentAllowance": extensions.get("privilegeOfCommentOnPost", 1),
        "style": {},
    }
    for k in [
        "backgroundMediaList",
        "backgroundColor",
        "coverMediaIndexList",
        "coverMediaList",
    ]:
        useful_extensions["style"].update({k: style.get(k)})

    blogId = str(uuid4())
    blog_data = ModelFabric.Construct(
        Community.Blogs,
        id=blogId,
        authorId=trigger_uid,
        title=title,
        content=content,
        blogType=blog_type,
        extensions=useful_extensions,
    )

    table = await db.get(f"x{ndcId}", "Blogs")
    await table.insert_one(blog_data)

    blog_info = await Blog.Info(blog_data, db, ndcId=ndcId, trigger_uid=trigger_uid)

    await db.close()
    return Base.Answer({"blog": blog_info}, spent_time=timestamp() - t1)


# delete comment from blog


@blog_methods.delete("/g/s/blog/{blogId}/comment/{commentId}")
@blog_methods.delete("/g/s/item/{blogId}/comment/{commentId}")
@blog_methods.delete("/x{ndcId}/s/blog/{blogId}/comment/{commentId}")
@blog_methods.delete("/x{ndcId}/s/item/{blogId}/comment/{commentId}")
async def delete_blog_comment(
    request: Request, blogId: str, commentId: str, ndcId: int = 0
):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")
    blog_info = await table.find_one({"id": blogId})
    if not blog_info:
        await db.close()
        return Errors.DataNotExist(timestamp() - t1)

    wall_data = blog_info.get("wall", {})
    if commentId not in wall_data:
        await db.close()
        return Errors.DataNotExist(timestamp() - t1)

    wm = wall_data[commentId]
    if wm["authorId"] != trigger_uid and blog_info["authorId"] != trigger_uid:
        await db.close()
        return Errors.NotEnoughRights(timestamp() - t1)

    unset_fields = {f"wall.{commentId}": ""}
    if wm.get("isSubWM") is False:
        for sub_id in wm.get("subWMs", []):
            if sub_id in wall_data:
                unset_fields[f"wall.{sub_id}"] = ""
    else:
        for parent_id, parent_info in wall_data.items():
            if commentId in parent_info.get("subWMs", []):
                await table.update_one(
                    {"id": blogId},
                    {"$pull": {f"wall.{parent_id}.subWMs": commentId}},
                )
                break

    await table.update_one({"id": blogId}, {"$unset": unset_fields})
    await db.close()
    return Base.Answer(spent_time=timestamp() - t1)


# vote for blog comment


@blog_methods.post("/g/s/blog/{blogId}/comment/{commentId}/vote")
@blog_methods.post("/g/s/item/{blogId}/comment/{commentId}/vote")
@blog_methods.post("/x{ndcId}/s/blog/{blogId}/comment/{commentId}/vote")
@blog_methods.post("/x{ndcId}/s/item/{blogId}/comment/{commentId}/vote")
async def vote_blog_comment(
    request: Request, blogId: str, commentId: str, ndcId: int = 0
):
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
    table = await db.get(f"x{ndcId}", "Blogs")
    blog_info = await table.find_one({"id": blogId})
    if not blog_info or commentId not in blog_info.get("wall", {}):
        await db.close()
        return Errors.DataNotExist(timestamp() - t1)

    if value == 1:
        await table.update_one(
            {"id": blogId},
            {
                "$addToSet": {f"wall.{commentId}.upvotes": trigger_uid},
                "$pull": {f"wall.{commentId}.downvotes": trigger_uid},
            },
        )
    elif value == -1:
        await table.update_one(
            {"id": blogId},
            {
                "$addToSet": {f"wall.{commentId}.downvotes": trigger_uid},
                "$pull": {f"wall.{commentId}.upvotes": trigger_uid},
            },
        )
    else:
        await db.close()
        return Errors.InvalidRequest(timestamp() - t1)

    await db.close()
    return Base.Answer(spent_time=timestamp() - t1)


# remove vote from blog comment


@blog_methods.delete("/g/s/blog/{blogId}/comment/{commentId}/vote")
@blog_methods.delete("/g/s/item/{blogId}/comment/{commentId}/vote")
@blog_methods.delete("/x{ndcId}/s/blog/{blogId}/comment/{commentId}/vote")
@blog_methods.delete("/x{ndcId}/s/item/{blogId}/comment/{commentId}/vote")
async def remove_blog_comment_vote(
    request: Request, blogId: str, commentId: str, ndcId: int = 0
):
    t1 = timestamp()
    if not request.state.session["validsession"]:
        return Errors.InvalidSession(timestamp() - t1)

    trigger_uid = request.state.session["uid"]

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")

    await table.update_one(
        {"id": blogId},
        {
            "$pull": {
                f"wall.{commentId}.upvotes": trigger_uid,
                f"wall.{commentId}.downvotes": trigger_uid,
            }
        },
    )

    await db.close()
    return Base.Answer(spent_time=timestamp() - t1)


# see who voted for blog comment


@blog_methods.get("/g/s/blog/{blogId}/comment/{commentId}/vote")
@blog_methods.get("/g/s/item/{blogId}/comment/{commentId}/vote")
@blog_methods.get("/x{ndcId}/s/blog/{blogId}/comment/{commentId}/vote")
@blog_methods.get("/x{ndcId}/s/item/{blogId}/comment/{commentId}/vote")
async def get_blog_comment_voters(
    request: Request,
    blogId: str,
    commentId: str,
    ndcId: int = 0,
    start: int = 0,
    size: int = 25,
):
    t1 = timestamp()

    db = await Database().init()
    table = await db.get(f"x{ndcId}", "Blogs")
    blog = await table.find_one({"id": blogId})
    if blog is None:
        await db.close()
        return Base.Answer({"userProfileList": []}, spent_time=timestamp() - t1)

    try:
        comment = blog["wall"][commentId]
        votes = comment.get("upvotes", []) + comment.get("downvotes", [])
        votes_selected = votes[start : start + size]
    except Exception:
        await db.close()
        return Base.Answer({"userProfileList": []}, spent_time=timestamp() - t1)

    xndc_users = await db.get(f"x{ndcId}", "Users")
    trigger_uid = request.state.session.get("uid")
    voters_list = [
        User.GetUserInfo(u, ndcId=ndcId, triggerUserId=trigger_uid)
        for item in votes_selected
        if (u := await xndc_users.find_one({"id": item}))
    ]

    await db.close()
    return Base.Answer({"userProfileList": voters_list}, spent_time=timestamp() - t1)
