import uuid
from typing import IO, Literal

from botocore.exceptions import NoCredentialsError
from loguru import logger
from starlette.exceptions import HTTPException
from types_aiobotocore_s3.client import S3Client

from child_tracker_auth.settings import settings


async def upload_file_to_storage(
    s3_client: S3Client,
    file: IO,
    bucket_name: str,
    file_extension: str,
    content_type_name: Literal["image"] = "image",
):
    def progress_callback(bytes_transferred):
        logger.info(
            f"Bucket: {bucket_name}. Key: {unique_filename}. Uploaded {bytes_transferred} bytes"
        )

    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    try:
        await s3_client.upload_fileobj(
            Fileobj=file,
            Bucket=bucket_name,
            Key=unique_filename,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": f"{content_type_name}/{file_extension}",
            },
            Callback=progress_callback,
        )
        url = f"{settings.storage_endpoint_url}/{bucket_name}/{unique_filename}"
        return url
    except NoCredentialsError:
        raise HTTPException(status_code=400, detail="S3 credentials not available")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error uploading file to S3: {str(e)}"
        )
