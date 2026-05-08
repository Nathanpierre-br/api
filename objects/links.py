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
                    "fullPath": "6666666/sonicexe",
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
                    "fullPath": "6666666/sonicexe",
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
                    "fullPath": "sonicexe-666666",
                    "shortCode": data["code"],
                    "shareURLFullPath": Config.SITE_BASE_URL
                    + "/web/x0/chat-thread/"
                    + data["objectId"],
                    "objectType": data["objectType"],
                }
            },
        }
        return {"linkInfoV2": obj, "linkInfo": obj}
