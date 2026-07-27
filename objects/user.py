from typing import Union

from .medialist import MediaList
from helpers.store import build_avatar_frame_icon

class User:
    @staticmethod
    def OwnSensetiveProfile(row):
        return {
            "username": None,
            "status": row.get("status", 0),
            "uid": row["id"],
            "modifiedTime": row.get("modifiedTime"),
            "createdTime": row["createdTime"],
            "twitterID": None,
            "googleID": None,
            "appleID": None,
            "facebookID": None,
            "role": row.get("role", 0),
            "aminoIdEditable": True,
            "aminoId": row["aminoId"],
            "activation": 1,
            "phoneNumberActivation": 0,
            "emailActivation": 1,
            "nickname": row.get("nickname"),
            "mediaList": MediaList.List(row.get("mediaList")),
            "icon": row.get("icon"),
            "securityLevel": 3,  # idk what is it
            "phoneNumber": None,
            "membership": None,
            "advancedSettings": {"analyticsEnabled": 0},
            "email": row["email"],
            "extensions": {
                "isMemberOfTeamAmino": row.get("isTeamMember", False),
                "contentLanguage": row.get("lang", "en"),
                "adsFlags": 2147483647,  # change to hide ads
                "adsLevel": 2,  # change to hide ads
                "deviceInfo": {
                    "lastClientType": 100  # i dont wanna store in memory that, its useless bro
                },
                "popupConfig": {
                    "ads": {"status": 0, "lastPopupTime": "1970-01-01T00:00:00Z"}
                },
                "mediaLabAdsMigrationAugust2020": True,
                "adsEnabled": False,
            },
        }

    @staticmethod
    def OwnNonSensetiveProfile(
        row, ndcId: int = 0, extensions: dict = {}, membershipStatus: int = 0
    ):
        """
        ndcId for another communities
        triggerUserId is who triggered this shit
        """
        ndcId = int(ndcId)
        return {
            "status": row["status"],
            "uid": row["id"],
            "modifiedTime": row["modifiedTime"],
            "createdTime": row["createdTime"],
            "role": row.get("role", 0),
            "aminoId": row.get("aminoId"),
            "nickname": row["nickname"],
            "tagList": row.get("tagList", []),
            "mediaList": MediaList.List(row.get("mediaList")),
            "icon": row.get("icon"),
            "accountMembershipStatus": int(row.get("isPaidSubscriber", 0)),
            "ndcId": ndcId,  # 0 is global
            "isGlobal": ndcId == 0,
            "reputation": 0,  # if ndcId == 0 else row["reputation"],
            "level": 0,  # if ndcId == 0 else row["level"],
            "mood": None,  # if ndcId == 0 else row["mood"],
            "content": ((row.get("description") or "").strip()),
            "joinedCount": len(row["following"]),
            "followingStatus": 0,
            "membersCount": len(row["whoFollows"]),
            "storiesCount": 0,
            "blogsCount": (
                0 if ndcId else 0
            ),  # [TODO] when communitues will be implemented do that
            "postsCount": (
                0 if ndcId else 0
            ),  # [TODO] when communitues will be implemented do that
            "backgroundColor": row.get("backgroundColor"),
            "extensions": {
                "tagList": row.get("tagList", []),
                "customTitles": row.get("titles", []),
                "backgroundColor": row.get("backgroundColor"),
                "style": {
                    "backgroundColor": row.get("backgroundColor"),
                    "backgroundMediaList": MediaList.List(
                        row.get("backgroundMediaList")
                    ),
                },
                "isMemberOfTeamAmino": row.get("isTeamMember", False),
            }
            | extensions,
            "moodSticker": (
                # None if ndcId == 0 else row["mood"]
                None
            ),  # [TODO]: check wtf is this
            "consecutiveCheckInDays": (
                # None if ndcId == 0 else row["consecutiveDaysOfCheckIns"]
                None
            ),  # [TODO] when communitues will be implemented do that
            "onlineStatus": 2,  # [TODO]: check wtf is this
            "isNicknameVerified": bool(row.get("isVerified", False)),
            "verified": bool(len(row.get("tagList", []))),  # this fixes tagList! :D
            "notificationSubscriptionStatus": 0,
            "pushEnabled": True,
            "membershipStatus": membershipStatus,
            "commentsCount": len(row.get("wall", [])),
        }

    @staticmethod
    def OtherProfile(
        row,
        triggerUserId: Union[str, None] = None,
        ndcId: int = 0,
        extensions: dict = {},
        membershipStatus: int | None = None,
    ):
        ndcId = int(ndcId)
        followingStatus = 0
        if triggerUserId is None:
            followingStatus = 0
        elif triggerUserId in row["whoFollows"] and triggerUserId in row["following"]:
            followingStatus = 3
        elif triggerUserId in row["following"]:
            followingStatus = 2
        elif triggerUserId in row["whoFollows"]:
            followingStatus = 1
        else:
            followingStatus = 0

        if row["id"] == triggerUserId:
            followingStatus = 0

        if membershipStatus is not None:
            followingStatus = membershipStatus

        return {
            "status": row["status"],
            "uid": row["id"],
            "modifiedTime": row["modifiedTime"],
            "createdTime": row["createdTime"],
            "role": row.get("role", 0),
            "aminoId": row.get("aminoId"),
            "nickname": row["nickname"],
            "tagList": row.get("tagList", []),
            "mediaList": MediaList.List(row.get("mediaList", [])),
            "icon": None if row["icon"] == "" else row["icon"],
            "accountMembershipStatus": int(row.get("isPaidSubscriber")),
            "ndcId": ndcId,  # 0 is global
            "isGlobal": ndcId == 0,
            "reputation": 0 if ndcId == 0 else row["reputation"],
            "level": 0 if ndcId == 0 else row["level"],
            "mood": None if ndcId == 0 else row["mood"],
            "content": ((row.get("description") or "").strip()),
            "joinedCount": len(row["whoFollows"]),
            "followingStatus": followingStatus,
            "membersCount": len(row["followers"]),
            "storiesCount": 0,  # i will NOT implement stories, fuck them
            "blogsCount": (
                0 if ndcId else 0
            ),  # [TODO] when communitues will be implemented do that
            "postsCount": (
                0 if ndcId else 0
            ),  # [TODO] when communitues will be implemented do that
            "extensions": {
                "tagList": row.get("tagList", []),
                "isMemberOfTeamAmino": row.get("isTeamMember", False),
                "customTitles": row.get("titles", []),
                "style": {
                    "backgroundColor": row.get("backgroundColor"),
                    "backgroundMediaList": MediaList.List(
                        row.get("backgroundMediaList")
                    ),
                },
            }
            | extensions,
            "moodSticker": (
                # None if ndcId == 0 else row["mood"]
                None
            ),  # [TODO]: check wtf is this
            "consecutiveCheckInDays": (
                # None if ndcId == 0 else row["consecutiveDaysOfCheckIns"]
                None
            ),  # [TODO] when communitues will be implemented do that
            "onlineStatus": 2,  # [TODO]: check wtf is this
            "isNicknameVerified": bool(row.get("isVerified", False)),
            "verified": bool(len(row.get("tagList", []))),  # this fixes tagList! :D
            "notificationSubscriptionStatus": 0,
            "pushEnabled": True,
            "membershipStatus": membershipStatus,
            "commentsCount": len(row["wall"]),
        }

    # [NOTE] onlineStatus : 1 when online, 2 when not
    # [NOTE] allowance : 1 when all, 2 when followers, 3 if not at all
    @staticmethod
    def GetUserInfo(
        row,
        ndcId: int = 0,
        triggerUserId: Union[str, None] = None,
        extensions: dict = {},
        membershipStatus: int | None = None,
    ):
        ndcId = int(ndcId)
        followingStatus = 0
        if triggerUserId is None:
            followingStatus = 0
        elif triggerUserId in row["whoFollows"] and triggerUserId in row["following"]:
            followingStatus = 3
        elif triggerUserId in row["following"]:
            followingStatus = 2
        elif triggerUserId in row["whoFollows"]:
            followingStatus = 1
        else:
            followingStatus = 0

        if row["id"] == triggerUserId:
            followingStatus = 0

        if membershipStatus is not None:
            followingStatus = membershipStatus

        iconFrame = row.get("iconFrame")
        if iconFrame is None: iconFrame = {}

        return {
            "iconFrameId": iconFrame.get("frameId"),
            "avatarFrame": iconFrame or None,
            "status": row["status"],
            "uid": row["id"],
            "modifiedTime": row["modifiedTime"],
            "createdTime": row["createdTime"],
            "role": row.get("role", 0),
            "aminoId": row.get("aminoId"),
            "nickname": row["nickname"],
            "tagList": row.get("tagList", []),
            "fanClubList": [],
            "mediaList": MediaList.List(row.get("mediaList", [])),
            "icon": row.get("icon"),
            "accountMembershipStatus": int(row.get("isPaidSubscriber", 0)),
            "ndcId": ndcId,  # 0 is global
            "isGlobal": ndcId == 0,
            "reputation": row.get("reputation", 0),
            "level": 0 if ndcId == 0 else row.get("level", 0),
            "mood": None if ndcId == 0 else row.get("mood"),
            "moodSticker": (
                None if ndcId == 0 else row.get("mood")
            ),  # [TODO]: check wtf is this
            "content": ((row.get("description") or "").strip()),
            "joinedCount": len(row["following"]),
            "followingStatus": followingStatus,
            "membersCount": len(row["whoFollows"]),
            "storiesCount": 0,  # i will NOT implement stories, fuck them
            "blogsCount": (
                0 if ndcId else 0
            ),  # [TODO] when communitues will be implemented do that
            "postsCount": (
                0 if ndcId else 0
            ),  # [TODO] when communitues will be implemented do that
            "extensions": {
                "tagList": row.get("tagList", []),
                "isMemberOfTeamAmino": row.get("isTeamMember", False),
                "customTitles": row.get("titles", []),
                "privilegeOfCommentOnUserProfile": row["allowanceWriteToWall"],
                "privilegeOfChatInviteRequest": row["allowanceWriteToPM"],
                "coverAnimation": "none",
                "deviceInfo": {
                    "lastClientType": 100  # [TODO]: WTF IS LAST CLIENT TYPE WHY THEY SAVE IT AND GIVE IT TO RANDOM USER WHAT THE ACTUAL FUCK BRO
                },
                "contentLanguage": row.get("lang", "en"),
                "style": {
                    "backgroundColor": row.get("backgroundColor"),
                    "backgroundMediaList": MediaList.List(
                        row.get("backgroundMediaList")
                    ),
                },
                "defaultBubbleId": "85045ed8-b05b-40de-907e-ec886889d086",
                "iconFrameId": "f3f280c5-a41a-4aa8-933a-4d740d67804e",
            }
            | extensions,
            "consecutiveCheckInDays": (
                None if ndcId == 0 else row.get("consecutiveDaysOfCheckIns", 0)
            ),  # [TODO] when communitues will be implemented do that
            "onlineStatus": 2,  # [TODO]: check wtf is this
            "isNicknameVerified": bool(row.get("isVerified", False)),
            "verified": bool(len(row.get("tagList", []))),  # this fixes tagList! :D
            "notificationSubscriptionStatus": 0,
            "pushEnabled": True,
            "membershipStatus": membershipStatus,
            "commentsCount": len(row["wall"]),
            "itemsCount": len(row.get("purchasedItems", {}).get("frames", []))
            + len(row.get("purchasedItems", {}).get("bubbles", [])),
            "visitPrivacy": 1,
            "visitorsCount": 0,  # [TODO]: make visitors count as var in table and do smart count
        }

    """
        "iconFrame":{
            "status":0,
            "ownershipStatus":1,
            "version":1,
            "resourceUrl":"http://af1.aminoapps.com/packages/8105/828d84a47df292b765d47b71d1dfbad2b347ce60.zip",
            "name":"Gray",
            "icon":"http://af1.aminoapps.com/8105/1c67b12dec2dfb63e8d0a96f735cd4f8238eff6c_00.gif",
            "frameType":1,
            "frameId":"93c220b6-2460-4c26-bde1-52095fffd6cd"
        }
    """
