from helpers.routers.cachable import CachableRoute
from helpers.imageTools import ImageTools
from string import ascii_letters, digits
from fastapi import APIRouter, Request
from time import time as timestamp
from helpers.config import Config
from boto3 import resource
from random import choice
from objects import *

# import sys
# sys.path.append('../')

def detect_file_ext(data: bytes) -> str | None:
    if len(data) < 12:
        return None

    # JPEG
    if data.startswith(b'\xff\xd8\xff'):
        return ".jpeg"
    # PNG
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return ".png"
    # GIF
    if data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return ".gif"
    # WebP
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return ".webp"
    
    return None

upload_media = APIRouter()
upload_media.route_class = CachableRoute

@upload_media.post("/g/s/media/upload")
async def upload(request: Request):
    t1 = timestamp()
    if not request.state.session.get("uid"):
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
    if file_ext == "":
        return Errors.InvalidMediaContent(spent_time=timestamp() - t1)

    # generating filename
    filename = "".join([choice(ascii_letters + digits) for _ in range(64)]) + file_ext

    # compress + resize if needed
    body = ImageTools.compress(body, file_ext[1:])

    # upload file
    s3.Bucket(Config.S3_BUCKET_NAME).put_object(Key=filename, Body=body)
    return Base.Answer(
        {"mediaValue": Config.MEDIA_BASE_URL + filename}, timestamp() - t1
    )


@upload_media.post("/g/s/media/upload/target/{target}")
async def upload_with_target(request: Request, target: str):
    t1 = timestamp()
    if not request.state.session.get("uid"):
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
    if file_ext == "":
        return Errors.InvalidMediaContent(spent_time=timestamp() - t1)

    # generating filename
    filename = "".join([choice(ascii_letters + digits) for _ in range(64)]) + file_ext

    # compress + resize if needed
    body = ImageTools.compress(body, file_ext[1:])

    # upload file
    s3.Bucket(Config.S3_BUCKET_NAME).put_object(Key=filename, Body=body)

    return Base.Answer(
        {"mediaValue": Config.MEDIA_BASE_URL + filename}, timestamp() - t1
    )
