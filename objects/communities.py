from hashlib import sha256
from typing import Union

from helpers.database.mongo import Database

from .medialist import MediaList
from .user import User

"""
this is top tier bullshit
"""
PAGES = {
    "defaultList": [
        #        {"url": "ndc://leaderboards", "alias": None, "id": "leaderboards-default"},
        {"url": "ndc://featured", "alias": None, "id": "featured-default"},
        {"url": "ndc://my-chats", "alias": None, "id": "chat-default"},
        {"url": "ndc://public-chats", "alias": None, "id": "chat-public-chats"},
        {"url": "ndc://latest-posts", "alias": None, "id": "post-latest-feed"},
        {"url": "ndc://following-feed", "alias": None, "id": "post-following-feed"},
        {"url": "ndc://image-posts", "alias": None, "id": "post-image-posts"},
        {"url": "ndc://blogs", "alias": None, "id": "post-blogs"},
        #        {"url": "ndc://quizzes", "alias": None, "id": "post-quizzes"},
        #        {
        #            "url": "ndc://quizzes/best",
        #            "alias": None,
        #            "id": "post-best-quizzes",
        #            "parentId": "post-quizzes",
        #        },
        #        {
        #            "url": "ndc://quizzes/trending",
        #            "alias": None,
        #            "id": "post-trending-quizzes",
        #            "parentId": "post-quizzes",
        #        },
        #        {
        #            "url": "ndc://quizzes/latest",
        #            "alias": None,
        #            "id": "post-latest-quizzes",
        #            "parentId": "post-quizzes",
        #        },
        #        {"url": "ndc://link-posts", "alias": None, "id": "post-link-posts"},
        {"url": "ndc://questions", "alias": None, "id": "post-questions"},
        {"url": "ndc://polls", "alias": None, "id": "post-polls"},
        #        {"url": "ndc://stories", "alias": None, "id": "post-stories"},
        #        {"url": "ndc://shared-folder", "alias": None, "id": "shared-folder"},
        #        {
        #            "url": "ndc://shared-folder/albums",
        #            "alias": None,
        #            "id": "shared-folder-albums",
        #            "parentId": "shared-folder",
        #        },
        #        {
        #            "url": "ndc://shared-folder/photos",
        #            "alias": None,
        #            "id": "shared-folder-photos",
        #            "parentId": "shared-folder",
        #        },
        #        {"url": "ndc://catalog", "alias": None, "id": "catalog-default"},
        #        {
        #            "url": "ndc://blog-categories",
        #            "alias": None,
        #            "id": "topic-categories-default",
        #        },
        {"url": "ndc://guidelines", "alias": None, "id": "guidelines"},
    ],
    "customList": [],
}


class Communities:
    @staticmethod
    def ModuleInfo(module_data: dict):
        return {
            "enabled": module_data.get("enabled", True),
            "privilege": {
                "type": module_data.get("accessType", 1),
                "minLevel": module_data.get("minLevel", 3),
            },
        }

    @staticmethod
    async def Info(
        ndcId: int | dict,
        connection=None,
        trigger_uid: Union[str, None] = None,
    ):
        if not connection:
            connection = await Database().init()
        if isinstance(ndcId, int) or isinstance(ndcId, str):
            comms = connection.get(table="Communities")
            data = await comms.find_one({"id": ndcId})
        else:
            data = ndcId
            ndcId = data["id"]

        # host_global = connection.get(table="Users").find_one({"id": data["agent"]})
        table = connection.get(f"x{ndcId}", "Users")
        host_xndcId = await table.find_one({"id": data["agent"]})
        agent = User.OwnNonSensetiveProfile(host_xndcId, ndcId) if host_xndcId else None

        membershipStatus = 0
        if trigger_uid and (
            trigger_uid == data.get("agent")
            or trigger_uid in data.get("memberList", [])
        ):
            membershipStatus = 1

        conf = data.get("configuration", {})
        mods = conf.get("modules", {})

        chat_mod = mods.get("chat", {})
        blog_mod = mods.get("blog", {})
        poll_mod = mods.get("poll", {})
        image_mod = mods.get("image", {})
        question_mod = mods.get("question", {})
        return {
            "agent": agent,
            "ndcId": ndcId,
            "name": data["name"],
            "link": "http://altamino.top/c/" + data["aminoId"],
            "endpoint": data["aminoId"],
            "membershipStatus": membershipStatus,
            "icon": data["icon"],
            "status": data["status"],
            "membersCount": data.get("membersCount", 0),
            "joinType": data.get("joinType", 0),
            "content": data.get("description", ""),
            "tagline": data.get("tagline", ""),
            "templateId": data.get("templateId", 9),
            "communityHeat": data.get("heat", 0.00),
            "extensions": {},
            "createdTime": data.get("createdTime", "2023-01-01T12:00:00Z"),
            "modifiedTime": data.get("modifiedTime", "2023-01-01T12:00:00Z"),
            "userAddedTopicList": [],
            "searchable": True,
            "influencerList": [],
            "primaryLanguage": data.get("lang", "en"),
            "isStandaloneAppDeprecated": False,
            "listedStatus": data.get("listedStatus", 2),
            "probationStatus": 0,
            "themePack": {
                "themeColor": data.get("themeColor", "#1B1C43"),
                "themePackUrl": data.get("themeUrl"),
                "themePackHash": data.get(
                    "themeHash",
                    sha256(
                        data.get("themeUrl", "https://trolo.lol/example").encode(
                            "utf-8"
                        )
                    ).hexdigest(),
                ),
                "themePackRevision": data.get("themeRevision"),
            },
            "mediaList": [],  # for description
            "isStandaloneAppMonetizationEnabled": False,
            "activeInfo": {},
            "configuration": {
                "page": PAGES,
                "module": {
                    "post": {
                        "enabled": True,
                        "postType": {
                            "publicChatRooms": Communities.ModuleInfo(chat_mod),
                            "blog": Communities.ModuleInfo(blog_mod),
                            "poll": Communities.ModuleInfo(poll_mod),
                            "image": Communities.ModuleInfo(image_mod),
                            "question": Communities.ModuleInfo(question_mod),
                        },
                    },
                    "chat": {
                        "enabled": chat_mod.get("enabled", True),
                        "spamProtectionEnabled": True,
                        "avChat": {
                            "screeningRoomEnabled": False,
                            "audioEnabled": True,
                            "videoEnabled": False,
                            "audio2Enabled": True,
                        },
                        "publicChat": Communities.ModuleInfo(chat_mod),
                    },
                },
                "appearance": {
                    "leftSidePanel": {
                        "style": {  # there is possible to add icon, i need example community infos
                            "iconColor": None,
                        },
                        "navigation": {
                            "level1": conf.get(
                                "sidepanelTopNav",
                                [
                                    {"id": "guidelines"},
                                    {"id": "chat-default"},
                                    {"id": "chat-public-chats"},
                                ],
                            ),
                            "level2": conf.get("sidepanelBottomNav", []),
                        },
                    },
                    "homePage": {
                        "navigation": conf.get(
                            "homepageNav",
                            [
                                {"id": "guidelines"},
                                {"id": "post-latest-feed"},
                                {"id": "chat-public-chats", "isStartPage": True},
                            ],
                        )
                    },
                },
            },
            "advancedSettings": {
                "pollMinFullBarVoteCount": 10,
                "welcomeMessageEnabled": conf.get("welcomeMessageEnabled", False),
                "welcomeMessageText": conf.get("welcomeMessage", ""),
                "catalogEnabled": True,  # ???
                "defaultRankingTypeInLeaderboard": 1,
                "frontPageLayout": conf.get("frontPageLayout", 1),
            },
            "communityHeadList": [],
            "promotionalMediaList": [MediaList.Item(data["coverUrl"])]
            if "coverUrl" in data
            else None,
        }

    """
    [TODO]
    configuration!
    """

    """
    [NOTE]
    This is what we need to implement later.
    Here are real examples what server sends.

    userAddedTopicList:
    {
      "topicId": 17328,
      "style": {
        "backgroundColor": "#ECCA41"
      },
      "name": "Аниме"
    }

    influencerList:
    basically, user with influencerInfo obj:
    {
      "pinned": false,
      "createdTime": "2024-05-01T21:53:14Z",
      "fansCount": 179,
      "monthlyFee": 20
    }

    themePack:
    wtf is hash and how it calculated
    {
        "themeColor": "#34754e",
        "themePackHash": "ea6f312f63cb8fedbe2145f7967d39cb", # ???
        "themePackRevision": 130,
        "themePackUrl": "http://theme.aminoapps.com/x156542274-rev130.ndthemepack"
    }

    communityHeadList:
    basically list with all admins there
    idk really why they need to do it, will not
    add it for now

    extensions:
    also idk why we need it for now
    {
        "communityNameAliases": "Anime,Аниме",
        "iTagIdList": [
            100006
        ]
    }
    """
