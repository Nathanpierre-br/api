# import sys
# sys.path.append('../')
from helpers.config import Config


class Links:
    @staticmethod
    def User(data: dict):
        ndcId = data.get("ndcId", 0)
        loc = "g" if ndcId == 0 else f"x{ndcId}"
        obj = {
            "path": f"{loc}/user-profile/{data['objectId']}",
            "extensions": {
                "linkInfo": {
                    "objectId": data["objectId"],
                    "shareURLShortCode": Config.SITE_BASE_URL + "/u/" + data["code"],
                    "targetCode": 1,
                    "ndcId": data.get("ndcId", 0),
                    "fullPath": f"ndc://{loc}/user-profile/{data['objectId']}",
                    "shortCode": data.get("code"),
                    "shareURLFullPath": Config.SITE_BASE_URL + "/u/" + data["code"],
                    "objectType": data["objectType"],
                }
            },
        }
        return {"linkInfoV2": obj, "linkInfo": obj}

    @staticmethod
    def Blog(data: dict):
        ndcId = data.get("ndcId", 0)
        loc = "g" if ndcId == 0 else f"x{ndcId}"
        obj = {
            "path": f"{loc}/blog/{data['objectId']}",
            "extensions": {
                "linkInfo": {
                    "objectId": data["objectId"],
                    "shareURLShortCode": Config.SITE_BASE_URL + "/p/" + data["code"],
                    "targetCode": 1,
                    "ndcId": ndcId,
                    "fullPath": f"ndc://{loc}/blog/{data['objectId']}",
                    "shortCode": data["code"],
                    "shareURLFullPath": Config.SITE_BASE_URL + "/p/" + data["code"],
                    "objectType": data["objectType"],
                }
            },
        }
        return {"linkInfoV2": obj, "linkInfo": obj}

    @staticmethod
    def Chat(data: dict):
        ndcId = data.get("ndcId", 0)
        loc = "g" if ndcId == 0 else f"x{ndcId}"
        obj = {
            "path": f"{loc}/chat-thread/{data['objectId']}",
            "extensions": {
                "linkInfo": {
                    "objectId": data["objectId"],
                    "shareURLShortCode": Config.SITE_BASE_URL + "/p/" + data["code"],
                    "targetCode": 1,
                    "ndcId": ndcId,
                    "fullPath": f"ndc://{loc}/chat-thread/{data['objectId']}",
                    "shortCode": data["code"],
                    "shareURLFullPath": Config.SITE_BASE_URL
                    + "/web/x0/chat-thread/"
                    + data["objectId"],
                    "objectType": data["objectType"],
                }
            },
        }
        return {"linkInfoV2": obj, "linkInfo": obj}

    @staticmethod
    def Community(data: dict):
        ndcId = data.get("ndcId", data.get("objectId", 0))
        loc = "g" if ndcId == 0 else f"x{ndcId}"
        obj = {
            "path": f"{loc}/community/{ndcId}",
            "extensions": {
                "linkInfo": {
                    "objectId": data["objectId"],
                    "shareURLShortCode": Config.SITE_BASE_URL + "/c/" + data["code"],
                    "targetCode": 1,
                    "ndcId": ndcId,
                    "fullPath": f"ndc://{loc}/community/{ndcId}",
                    "shortCode": data["code"],
                    "shareURLFullPath": Config.SITE_BASE_URL + "/web/x0/community/" + data["objectId"],
                    "objectType": data["objectType"],
                }
            },
        }
        return {"linkInfoV2": obj, "linkInfo": obj}