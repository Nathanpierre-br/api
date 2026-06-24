from functools import wraps
from json import dumps
from uuid import UUID

from helpers.aquarium import Aether
from helpers.config import Config
from helpers.processors.cache import CacheProcessor
from objects import Errors


class TurtleTime:
    second = 1
    minute = 60
    hour = 3600
    day = 86400


def turtlelimiter(
    limit: int = 3,
    period: int = TurtleTime.second,
    cooldown: int = TurtleTime.minute * 2,
    tag: str = "default",
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # if turtlelimiter is disabled, just simply walk around it
            if not Config.ENABLE_TURTLELIMIT:
                return await func(*args, **kwargs)

            request = kwargs.get("request")

            # if there is no valid session, just skipping it
            # since it probably requires authentication and
            # there is validauth_required decorator
            if not request.state.session.get(
                "validsession"
            ) or not request.state.session.get("uid"):
                return await func(*args, **kwargs)

            uid = request.state.session["uid"]
            # [WARN]: it should be like this, make it properly
            # i just dont have much time left to code this
            # ill fully back in november           -shader
            if uid == "80b66fa4-349c-4976-8b48-5b30bc48d1dc":
                return await func(*args, **kwargs)

            # we are rate limiting by user id since ip-based rate limiting
            # is easily can be bypassed using a VPN or proxy
            uid = UUID(uid).hex

            # for multi rate limiting
            inspector = Aether.encode(
                dumps({"case": tag, "user": uid}, ensure_ascii=False)
            ).decode()
            turtle = await CacheProcessor.Get(inspector, prefix="turtlelimiter:")
            if turtle is None:
                await CacheProcessor.Make(
                    inspector,
                    prefix="turtlelimiter:",
                    value=1,
                    expiring_after=period,
                )
                return await func(*args, **kwargs)

            # if user has not exceeded the limit, increment the turtle counter
            if int(turtle) <= limit:
                await CacheProcessor.Update(
                    inspector, prefix="turtlelimiter:", increment=True
                )
                return await func(*args, **kwargs)

            # if user has exceeded the limit - well, solve the captcha
            # also cooldown is resetted ([NOTE]: maybe will be removed, we need to test it)
            await CacheProcessor.Update(
                inspector, prefix="turtlelimiter:", expiring_after=cooldown
            )

            # Bypass for testing
            # return await func(*args, **kwargs)

            return Errors.VerificationRequired(
                Config.API_BASE_URL + "/api/v1/turtle/hello?inspector=" + inspector
            )

        return wrapper

    return decorator
