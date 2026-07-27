from .user import User
from .medialist import MediaList
from services.store import StoreService


class Comments:
    @staticmethod
    async def Parent(
        row,
        commentId: str,
        parentId: str,
        xndcid_users,
        triggerUserId: str | None = None,
        parentType: int = 0,
        ndcId: int = 0,
        extenstions: dict = {},
    ):
        upvotes = row.get("upvotes", [])
        downvotes = row.get("downvotes", [])

        votesSum = len(upvotes) - len(downvotes)
        voteValue = (
            1 if triggerUserId in upvotes else -1 if triggerUserId in downvotes else 0
        )

        author = await xndcid_users.find_one({"id": row["authorId"]}) or {}
        async with await StoreService.create(row["authorId"], ndcId) as svc:
            author["iconFrame"] = await svc.frame_icon(author.get("frameId"))

        return {
            "modifiedTime": row["modifiedTime"],
            "ndcId": ndcId,
            "votedValue": voteValue,
            "parentType": parentType,  # im guessing its for posts and etc
            "commentId": commentId,  # comment id
            "parentNdcId": ndcId,
            "mediaList": MediaList.List(row.get("mediaList", [])),
            "votesSum": votesSum,
            "subcommentsPreview": [],  # subcomments preview
            "author": User.GetUserInfo(author, ndcId),
            "content": row["content"],
            "extensions": {} | extenstions,
            "parentId": parentId,
            "createdTime": row["createdTime"],
            "subcommentsCount": len(row["subWMs"]),
            "type": 0,
        }

    @staticmethod
    async def Son(
        row,
        commentId: str,
        headCommentId: str,
        parentId: str,
        xndcid_users,
        triggerUserId: str | None = None,
        parentType: int = 0,
        ndcId: int = 0,
        extenstions: dict = {},
    ):
        upvotes = row.get("upvotes", [])
        downvotes = row.get("downvotes", [])

        votesSum = len(upvotes) - len(downvotes)
        voteValue = (
            1 if triggerUserId in upvotes else -1 if triggerUserId in downvotes else 0
        )

        author = await xndcid_users.find_one({"id": row["authorId"]}) or {}
        async with await StoreService.create(row["authorId"], ndcId) as svc:
            author["iconFrame"] = await svc.frame_icon(author.get("frameId"))

        return {
            "headCommentId": headCommentId,
            "modifiedTime": row["modifiedTime"],
            "ndcId": ndcId,
            "votedValue": voteValue,
            "parentType": parentType,  # im guessing its for posts and etc
            "commentId": commentId,  # comment id
            "parentNdcId": ndcId,
            "mediaList": MediaList.List(row.get("mediaList", [])),
            "votesSum": votesSum,
            "author": User.GetUserInfo(author, ndcId),
            "content": row["content"],
            "extensions": {} | extenstions,
            "parentId": parentId,
            "createdTime": row["createdTime"],
            "subcommentsCount": 0,
            "type": 0,
        }
