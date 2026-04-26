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
            "communityInfoMapping": {},
        },
        spent_time=timestamp() - t1,
    )


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
            return Errors.NoPermission(timestamp() - t1)

    # [MEDIA LIST CHECK SPACE START]

    # [MEDIA LIST CHECK SPACE END]

    blogId = str(uuid4())
    blog_data = ModelFabric.Construct(
        Community.Blogs,
        id=blogId,
        authorId=trigger_uid,
        title=title,
        content=content,
        blogType=blog_type,
        extensions=extensions,
    )

    table = await db.get(f"x{ndcId}", "Blogs")
    await table.insert_one(blog_data)

    blog_info = await Blog.Info(blog_data, db, ndcId=ndcId, trigger_uid=trigger_uid)

    await db.close()
    return Base.Answer({"blog": blog_info}, spent_time=timestamp() - t1)
