from datetime import UTC, datetime
from typing import Union

from fastapi.responses import JSONResponse

from helpers.processors.signature import SignatureProcessor


class Base:
    @staticmethod
    def Answer(
        data: dict = {},
        spent_time: Union[int, float] = 0.001,
        api_status_code: int = 0,
        api_message="OK",
        html_status_code: int = 200,
    ):
        final_data = {
            "api:statuscode": api_status_code,
            "api:duration": f"{round(spent_time + 0.001, 4)}s",
            "api:message": api_message,
            "api:timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        } | data
        headers = {"NDC-MSG-SIG": SignatureProcessor.Generate(final_data)}
        return JSONResponse(
            final_data,
            status_code=html_status_code,
            headers=headers,
        )

    @staticmethod
    def LiveLayerTopic(
        topic_name: str,
        users_count: int = 0,
        users_list: list = [],
        media_list: list | None = None,
    ):
        return {
            "topic": topic_name,
            "userProfileCount": users_count,
            "userProfileList": users_list,
            "mediaList": media_list,
        }
