import aioboto3
from botocore.config import Config
from fastapi import FastAPI
from loguru import logger
from types_aiobotocore_s3.client import S3Client

from child_tracker_auth.settings import settings

session = aioboto3.Session()


def create_storage_client() -> S3Client:
    sc = session.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url,
        region_name=settings.storage_region,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        config=Config(s3={"addressing_style": "path"}),
        verify=True,
    )
    return sc


async def on_startup_storage(app: FastAPI):
    logger.info("Fetch storage buckets")
    async with create_storage_client() as sc:
        buckets = await sc.list_buckets()
        bucket_names = []
        for bucket in buckets.get("Buckets", []):
            bucket_names.append(bucket["Name"])
        app.state.storage_bucket_names = bucket_names  # noqa
        return bucket_names


async def on_shutdown_storage(app: FastAPI):
    pass
