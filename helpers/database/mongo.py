from typing import Union

import motor.motor_asyncio

from ..config import Config


class Database:
    async def init(self) -> motor.motor_asyncio.AsyncIOMotorClient:
        self.__connection = motor.motor_asyncio.AsyncIOMotorClient(
            Config.MONGODB_CONNECTION_STRING, uuidRepresentation="pythonLegacy"
        )
        return self

    def get(
        self, database: str = Config.MONGODB_MAIN_DB, table: Union[None, str] = None
    ):
        return (
            self.__connection[database]
            if table is None
            else self.__connection[database][table]
        )

    def close(self):
        return self.__connection.close()

    @property
    def connection(self):
        return self.__connection
