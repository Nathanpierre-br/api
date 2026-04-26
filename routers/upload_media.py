from helpers.routers.cachable import CachableRoute
from helpers.functions import detect_file_ext
from helpers.imageTools import ImageTools
from string import ascii_letters, digits
from fastapi import APIRouter, Request
from time import time as timestamp
from helpers.config import Config
from boto3 import resource
from random import choice
from objects import Base, Errors
from io import BytesIO
from orjson import loads
from zipfile import ZipFile

from helpers.database.mongo import Database

upload_media = APIRouter()
upload_media.route_class = CachableRoute


@upload_media.post("/g/s/media/upload")
@upload_media.post("/x{ndcId}/s/media/upload")
@upload_media.post("/g/s/media/upload/target/{target}")
@upload_media.post("/x{ndcId}/s/media/upload/target/{target}")
async def upload(request: Request, ndcId: int = 0, target: str = ""):
    t1 = timestamp()
    uid = request.state.session.get("uid")
    if uid is None:
        return Errors.InvalidSession(timestamp() - t1)

    # this is getting data
    body = await request.body()

    if len(body) > Config.MAX_FILE_SIZE:
        return Errors.BigMediaContent(timestamp() - t1)

    # init s3 class
    s3 = resource(
        service_name=Config.S3_SERVICE_NAME,
        aws_access_key_id=Config.S3_ACCESS_KEY,
        aws_secret_access_key=Config.S3_SECRET_ACCESS_KEY,
        endpoint_url=Config.S3_ENDPOINT_URL,
    )

    # validating imagw and getting its type
    # [note]: its still not safe,
    # but better and still fast then content-type
    file_ext = detect_file_ext(body)
    is_zip = body.startswith(b"PK\x03\x04")
    if file_ext is None and not is_zip:
        return Errors.InvalidMediaContent(spent_time=timestamp() - t1)

    if is_zip:
        # themes are basically zips
        if target == "theme":
            # ain't trust anyone! better check if it's leader/agent/astral
            db = await Database.get(f"x{ndcId}", "Users")
            user_info = await db.get({"id": uid})
            if user_info.get("role") not in [100, 102, 200, 201, 250, 251, 555]:
                return Errors.NotEnoughRights()

            # if its valid zip we can get theme config and revision here
            # so that way we both checking theme and its config
            try:
                with BytesIO(body) as buffer:
                    with ZipFile(buffer) as zip_ref:
                        with zip_ref.open("theme_info.json") as f:
                            theme_config = loads(f.read())
                rev = theme_config["revision"]
            except Exception:
                return Errors.InvalidMediaContent(spent_time=timestamp() - t1)

            filename = Config.S3_NDCTHEMES_FOLDER + f"x{ndcId}-rev{rev}.ndthemepack"
        # leaving it here for maybe another use of this?
        else:
            return Errors.InvalidRequest(spent_time=timestamp() - t1)
    else:
        # generating filename
        filename = (
            Config.S3_IMAGES_FOLDER
            + "".join([choice(ascii_letters + digits) for _ in range(64)])
            + file_ext
        )

        # compress + resize if needed
        body = ImageTools.compress(body, file_ext[1:])

    # upload file
    s3.Bucket(Config.S3_BUCKET_NAME).put_object(Key=filename, Body=body)
    return Base.Answer(
        {"mediaValue": Config.MEDIA_BASE_URL + filename}, timestamp() - t1
    )
