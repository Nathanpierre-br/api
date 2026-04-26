from datetime import datetime, UTC
from pymongo import DESCENDING
from re import escape as regex_escape
from fastapi import APIRouter, Request
from time import time as timestamp
from typing import Union
from uuid import uuid4

from objects import Base, Errors, Blog
from helpers.functions import parse_page_token, calculate_page_tokens
from helpers.database.mongo import Database
from helpers.database.models import ModelFabric, Community
from helpers.routers.cachable import CachableRoute

blog_methods = APIRouter()
blog_methods.route_class = CachableRoute


@blog_methods.get("/x{ndcId}/s/feed/blog-recommended")
async def get_recommended_blogs(request: Request, ndcId: int):
    # mock for now
    return Base.Answer({"blogList": []})


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


@blog_methods.post("/x{ndcId}/s/blog/{blogId}/vote")
async def like_blog(request: Request, blogId: str, ndcId: int = 0):
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

    if value in [1, 4]:
        await table.update_one(
            {"id": blogId},
            {
                "$addToSet": {"upvote": trigger_uid},
                "$pull": {"downvote": trigger_uid},
            },
        )
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


@blog_methods.delete("/x{ndcId}/s/blog/{blogId}/vote")
async def unlike_blog(request: Request, blogId: str, ndcId: int = 0):
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


@blog_methods.post("/g/s/blog")
@blog_methods.post("/x{ndcId}/s/blog")
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
