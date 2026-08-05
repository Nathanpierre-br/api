from functools import wraps
from time import time as timestamp
from helpers.database.mongo import Database
from objects.errors import Errors


def strike_check(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # We need to find request and ndcId
        request = kwargs.get("request")
        if not request:
            # Try finding request in positional args if not in kwargs
            for arg in args:
                if hasattr(arg, "state"):  # Simple way to detect request object
                    request = arg
                    break

        if not request:
            return Errors.InvalidRequest()

        if not request.state.session.get("validsession"):
            return Errors.InvalidSession(lang=request.state.lang)

        trigger_uid = request.state.session.get("uid")
        if not trigger_uid:
            return Errors.InvalidSession(lang=request.state.lang)

        ndcId = kwargs.get("ndcId", 0)

        db = await Database().init()
        table = db.get(f"x{ndcId}", "Users")
        user = await table.find_one({"id": trigger_uid})
        db.close()

        if user and user.get("timeout_until", 0) > timestamp():
            return Errors.UserStruck(lang=request.state.lang)

        return await func(*args, **kwargs)

    return wrapper
