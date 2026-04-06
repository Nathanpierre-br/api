from typing import Union
from helpers.database.mongo import Database
from .user import User


class Communities:
    @staticmethod
    async def Info(
        ndcId: int | dict,
        connection=None,
        trigger_uid: Union[str, None] = None,
    ):
        if not connection:
            connection = await Database().init()
        if isinstance(ndcId, int) or isinstance(ndcId, str):
            comms = await connection.get("global", "Communities")
            data = await comms.find_one({"id": ndcId})
        else:
            data = ndcId
            ndcId = data["id"]

        # host_global = await connection.get(table="Users").find_one({"id": data["agent"]})
        table = await connection.get(f"x{ndcId}", "Users")
        host_xndcId = await table.find_one({"id": data["agent"]})
        agent = User.OwnNonSensetiveProfile(host_xndcId, ndcId) if host_xndcId else None

        membershipStatus = 0
        if trigger_uid and (
            trigger_uid == data.get("agent")
            or trigger_uid in data.get("memberList", [])
        ):
            membershipStatus = 1

        return {
            "agent": agent,
            "ndcId": ndcId,
            "name": data["name"],
            "link": "http://aminoapps.com/c/" + data["aminoId"],
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
            "updatedTime": data.get("updatedTime", "2023-01-01T12:00:00Z"),
            "userAddedTopicList": [],
            "searchable": True,
            "influencerList": [],
            "primaryLanguage": data.get("lang", "en"),
            "isStandaloneAppDeprecated": False,
            "listedStatus": data.get("listedStatus", 2),
            "probationStatus": 0,
            "themePack": {
                "themeColor": data.get("themeColor", "#000000"),
                "themePackUrl": data.get("themeUrl"),
                "themePackHash": data.get("themeHash"),
                "themePackRevision": data.get("themeRevision"),
            },
            "mediaList": [],  # for description
            "isStandaloneAppMonetizationEnabled": False,
            "activeInfo": {},
            "configuration": {},
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
    it's easy to implement, but we don't have any
    theme files. once we will get one on hand we
    will add support to them:
    {
        "themeColor": "#34754e",
        "themePackHash": "ea6f312f63cb8fedbe2145f7967d39cb", # ???
        "themePackRevision": 130, # ???
        "themePackUrl": "http://theme.aminoapps.com/x156542274-rev130.ndthemepack" # ???
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

    promotionalMediaList:
    also no idea for now
    [
      [
        100,
        "http://cm1.aminoapps.com/8994/3f565c7f774febc4f0624a439b58f8eda8f16416_00.jpg",
        null
      ]
    ]
    """
