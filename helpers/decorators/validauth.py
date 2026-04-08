from functools import wraps
from objects.errors import Errors


def validauth_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request or not request.state.session.get("validsession"):
            return Errors.InvalidSession()
        return await func(*args, **kwargs)

    return wrapper
