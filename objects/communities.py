from .user import User
from typing import Union
from datetime import datetime

# import sys
# sys.path.append('../')
from helpers.database.mongo import Database


class Communities:
    @staticmethod
    async def Info(
        ndcId: int | dict,
        connection=None,
        trigger_uid: Union[str, None] = None,
        g_users=None,
        xndc_users=None,
    ):
        if not connection:
            connection = await Database().init()
        if isinstance(ndcId, int) or isinstance(ndcId, str):
            comms = await connection.get("global", "Communities")
            data = await comms.find_one({"id": ndcId})
        else:
            data = ndcId

        if g_users:
            host_global = await g_users.find_one({"id": data["agent"]})
        else:
            users = await connection.get(table="Users")
            host_global = await users.find_one({"id": data["agent"]})

        if xndc_users:
            host_xndcId = await xndc_users.find_one({"id": data["agent"]})
        else:
            users = await connection.get(f"x{ndcId}", "Users")
            host_xndcId = await users.find_one({"id": data["agent"]})

        return {
            "ndcId": data["id"],
            "name": data["name"],
            "link": "http://aminoapps.com/c/" + data["aminoId"],
            "endpoint": data["aminoId"],
            "icon": data["icon"],
            "theme": data.get("theme", ""),
            "status": data["status"],
            "membersCount": 0,  # todo
            "joinType": 0,  # todo,
            "content": data.get("description"),
            "tagline": data.get("slogan"),
            "rules": data.get("rules"),
            "communityHeat": data.get("heat", 0.00),
            "extensions": {} | data.get("extensions", {}),
            "createdTime": data.get("createdTime", "2023-01-01T12:00:00Z"),
            "updatedTime": data.get("updatedTime", "2023-01-01T12:00:00Z"),
            "userAddedTopicList": data.get("tags", []),
            "searchable": True,
            "influencerList": [],
        }

        # db data
        """
    class Communities(Schema):
        staff = List(UUID(metadata={"as_string": True}), default=[])
        """

        # an example json
        """{
            "primaryLanguage": "ru",
            "probationStatus": 0,
            "listedStatus": 0,
            "isStandaloneAppDeprecated": false,
            "keywords": "keyword1, keyword2",
            "mediaList": [],
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
        }"""
