# import sys
# sys.path.append('../')
from helpers.config import Config


class Links:
    @staticmethod
    def User(data: dict):
        obj = {
            "path": f"g/user-profile/{data['objectId']}",
            "extensions": {
                "linkInfo": {
                    "objectId": data["objectId"],
                    "shareURLShortCode": Config.SITE_BASE_URL + "/u/" + data["code"],
                    "targetCode": 1,
                    "ndcId": data["ndcId"],
                    "fullPath": "6666666/sonicexe",
                    "shortCode": None,
                    "shareURLFullPath": Config.SITE_BASE_URL + "/u/" + data["code"],
                    "objectType": data["objectType"],
                }
            },
        }
        return {"linkInfoV2": obj, "linkInfo": obj}

    @staticmethod
    def Chat(data: dict):
        obj = {
            "path": f"g/chat-thread/{data['objectId']}",
            "extensions": {
                "linkInfo": {
                    "objectId": data["objectId"],
                    "shareURLShortCode": Config.SITE_BASE_URL + "/p/" + data["code"],
                    "targetCode": 1,
                    "ndcId": data["ndcId"],
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
