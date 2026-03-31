from .user import User
from typing import Union
from datetime import datetime

# import sys
# sys.path.append('../')
from helpers.database.mongo import Database


class Communities:
    @staticmethod
    async def Info(
        ndcId: int,
        connection=None,
        trigger_uid: Union[str, None] = None,
    ):
        if not connection:
            connection = await Database().init()
        comms = await connection.get("global", "Communities")
        data = await comms.find_one({"id": ndcId})

        if g_users != None:
            users = g_users
            host_global = await users.find_one({"id": data["hostId"]})
        else:
            users = await connection.get(table="Users")
            host_global = await users.find_one({"id": data["hostId"]})

        if xndc_users != None:
            users = xndc_users
            host_xndcId = await users.find_one({"id": data["hostId"]})
        else:
            users = await connection.get(f"x{ndcId}", "Users")
            host_xndcId = await users.find_one({"id": data["hostId"]})

        return {
            "ndcId": data["id"],
            "name": data["name"],
            "endpoint": data["aminoId"],
            "icon": data["icon"],
            "theme": data.get("theme", ""),
            "status": data["status"],
            "membersCount": 0,  # todo
            "joinType": 0,  # todo,
            "description": data.get("description"),
            "tagline": data.get("slogan"),
            "rules": data.get("rules"),
            "communityHeat": data.get("heat", 0.00),
            "extensions": {} | data.get("extensions", {}),
            "createdTime": data.get("createdTime", "2023-01-01T12:00:00Z"),
            "updatedTime": data.get("updatedTime", "2023-01-01T12:00:00Z"),
        }

        # db data
        """
    class Communities(Schema):
        agent = UUID(required=True, metadata={"as_string": True})
        staff = List(UUID(metadata={"as_string": True}), default=[])
        tags = List(String(), default=[])
        """

        # an example json
        {
            "link": "http://aminoapps.com",
            "primaryLanguage": "ru",
            "userAddedTopicList": [],
            "probationStatus": 0,
            "listedStatus": 0,
            "tagline": "Короткий слоган",
            "searchable": true,
            "isStandaloneAppDeprecated": false,
            "influencerList": [],
            "keywords": "keyword1, keyword2",
            "mediaList": [],
            "content": "Полное описание сообщества",
            "isStandaloneAppMonetizationEnabled": false,
            "templateId": 1,
            "promotionalMediaList": [],
            "themePack": {
                "themeColor": "#FFFFFF",
                "themePackHash": "abc123hash",
                "themePackRevision": 5,
                "themePackUrl": "https://example.com",
            },
            "configuration": {
                "appearance": {
                    "homePage": {"navigation": "home-nav-data"},
                    "leftSidePanel": {
                        "navigation": {
                            "level1": "top-panel-data",
                            "level2": "bottom-panel-data",
                        },
                        "style": {"iconColor": "#000000"},
                    },
                },
                "page": {"customList": []},
            },
            "advancedSettings": {
                "defaultRankingTypeInLeaderboard": 1,
                "frontPageLayout": 2,
                "hasPendingReviewRequest": false,
                "welcomeMessageEnabled": true,
                "welcomeMessageText": "Добро пожаловать!",
                "pollMinFullBarVoteCount": 5,
                "catalogEnabled": true,
                "leaderboardStyle": "classic",
                "facebookAppIdList": [],
                "newsfeedPages": [],
                "joinedBaselineCollectionIdList": [],
            },
            "activeInfo": {},
            "extensions": {"communityNameAliases": ["Alias1", "Alias2"]},
        }
