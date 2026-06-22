from typing import Union

from .medialist import MediaList
from .user import User


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
            blogs = connection.get(f"x{ndcId}", "Blogs")
            data = await blogs.find_one({"id": blogId})
        else:
            data = blogId

        if xndc_users is not None:
            author_data = await xndc_users.find_one({"id": data["authorId"]}) or {}
        else:
            xndc_users = connection.get(f"x{ndcId}", "Users")
            author_data = await xndc_users.find_one({"id": data["authorId"]}) or {}

        extensions = data.get("extensions", {})
        return {
            "author": User.GetUserInfo(
                author_data, ndcId=ndcId, triggerUserId=trigger_uid
            ),
            "blogId": data["id"],
            "title": data.get("title"),
            "content": data.get("content"),
            "type": data["blogType"],
            "status": data.get("status", 0),
            "votesCount": len(data.get("upvote", [])) - len(data.get("downvote", [])),
            "commentsCount": len(data.get("wall", [])),
            "ndcId": ndcId,
            "createdTime": data["createdTime"],
            "modifiedTime": data["modifiedTime"],
            "extensions": {
                "privilegeOfCommentOnPost": data.get("commentAllowance", 1),
            }
            | extensions,
            "mediaList": MediaList.List(data.get("mediaList", [])),
            "votedValue": (
                4
                if trigger_uid in data.get("upvote", [])
                else -1
                if trigger_uid in data.get("downvote", [])
                else 0
            ),
            "viewCount": 0,
        }
