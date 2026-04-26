from .user import User
from .medialist import MediaList

from typing import Union


class Blog:
    @staticmethod
    async def Info(
        blogId: str | dict,
        connection,
        ndcId: int = 0,
        trigger_uid: Union[str, None] = None,
        xndc_users=None,
    ):
        if isinstance(blogId, str):
            blogs = await connection.get(f"x{ndcId}", "Blogs")
            data = await blogs.find_one({"id": blogId})
        else:
            data = blogId

        if data is None:
            return None

        if xndc_users is not None:
            author_data = await xndc_users.find_one({"id": data["authorId"]}) or {}
        else:
            xndc_users = await connection.get(f"x{ndcId}", "Users")
            author_data = await xndc_users.find_one({"id": data["authorId"]}) or {}

        extensions = data.get("extensions", {})
        return {
            "author": User.GetUserInfo(
                author_data, ndcId=ndcId, triggerUserId=trigger_uid
            ),
            "blogId": data["id"],
            "title": data.get("title"),
            "content": data.get("content"),
            "type": data.get("blogType"),
            "status": data.get("status", 0),
            "votesCount": len(data.get("liked", [])),
            "commentsCount": len(data.get("wall", [])),
            "ndcId": ndcId,
            "createdTime": data["createdTime"],
            "modifiedTime": data["modifiedTime"],
            "extensions": {
                "privilegeOfCommentOnPost": data.get("commentAllowance", 1),
            }
            | extensions,
            "mediaList": MediaList.List(data.get("mediaList", [])),
            "votedValue": int(trigger_uid in data.get("liked", [])),
            "viewCount": 0,
        }
