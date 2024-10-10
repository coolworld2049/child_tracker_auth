import json
from contextlib import suppress
from datetime import date
from random import randint
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, UploadFile
from fastapi.params import Depends, Query, File
from loguru import logger
from mimesis import Internet
from sqlalchemy import select, and_, text, delete, or_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import Request

from child_tracker_auth import schemas
from child_tracker_auth.db.base import LogTable, FileTable, DeviceTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.schemas import log_type_values
from child_tracker_auth.security.oauth2 import get_current_member
from child_tracker_auth.settings import settings
from child_tracker_auth.storage.dependencies import (
    create_storage_client,
)
from child_tracker_auth.storage.service import upload_file_to_storage
from child_tracker_auth.web.api.const import date_from_default, date_to_default

internet = Internet()

router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
    dependencies=(
        [Depends(get_current_member)] if settings.environment == "prod" else None
    ),
)


@router.get("/{id}/logs", response_model=list[schemas.PydanticLog])
async def get_device_logs(
    id: int,
    offset: int = 0,
    limit: int = 100,
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    log_type: str | None = Query(None, enum=log_type_values),
    db: AsyncSession = Depends(get_db_session),
):
    q = select(LogTable).filter(
        and_(
            LogTable.device_id == id,
            LogTable.log_type == log_type,
            LogTable.date.between(date_from, date_to),
        )
    )
    q = q.offset(offset).limit(limit)
    rq = await db.execute(q)
    r = rq.scalars().all()
    logs = [schemas.PydanticLog(**x.__dict__) for x in r]
    return logs


@router.get("/files/mime-types", response_model=list[str])
async def get_files_mime_types(
    db: AsyncSession = Depends(get_db_session),
):
    q = select(FileTable.type.distinct()).filter(FileTable.type != "")
    rq = await db.execute(q)
    r = rq.scalars().all()
    return r


@router.get("/files", response_model=list[schemas.PydanticFileRespone])
async def get_device_files(
    device_id: int | None = None,
    section_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
    mime_type: list[str] | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    and_f = []
    or_f = []
    if device_id:
        and_f.append(FileTable.device_id == device_id)
    if section_id:
        and_f.append(FileTable.section_id == section_id)
    if mime_type:
        or_f.extend([FileTable.type.ilike(f"%{x}%") for x in mime_type])
    q = select(FileTable).filter(and_(*and_f), or_(*or_f))
    q = q.offset(offset).limit(limit)
    rq = await db.execute(q)
    r = rq.scalars().all()
    if len(r) < 1:
        return []
    files = [
        schemas.PydanticFileRespone(
            **x.__dict__, url=f"https://child-tracker.uz{x.path}"
        )
        for x in r
    ]
    return files


@router.get(
    "/{id}/phone_book",
    response_model=list[schemas.PhoneBookItem],
)
async def get_device_phone_book(
    id: int,
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    q = text(
        f"""
    select
        l.name as name
    from
        logs l
    where l.log_type in ('in_call', 'out_call', 'out_sms')
    limit :limit offset :offset
    """
    )
    rq = await db.execute(
        q,
        {
            "limit": limit,
            "offset": offset,
            "device_id": id,
        },
    )
    r = rq.scalars().all()

    if len(r) < 1:
        return []

    phones = [schemas.Phone(name=x) for x in
              r]
    phone_book = [schemas.PhoneBookItem(name=x.sub or x.name, phone=x.phone) for x in
                  phones]
    unique_phone_book = list({item.phone: item for item in phone_book}.values())

    unique_phone_numbers = set()
    unique_phone_book = []
    for item in phone_book:
        if item.phone not in unique_phone_numbers:
            unique_phone_numbers.add(item.phone)
            unique_phone_book.append(item)
    return unique_phone_book


@router.get(
    "/{id}/calls",
    response_model=dict[str, list[schemas.PhoneCall]],
    description="dict key - date e.g 2024-08-22",
)
async def get_device_calls(
    id: int,
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    q = text(
        f"""
select
    l.name as name,
    l.log_type as type,
    l.duration as duration,
    l.`date` as date
from
    logs l
join devices d on
    d.id = l.device_id
where
    d.id = :device_id
    and l.log_type in ('in_call', 'out_call', 'out_sms')
limit :limit OFFSET :offset
    """
    )
    rq = await db.execute(
        q,
        {
            "limit": limit,
            "offset": offset,
            "device_id": id,
        },
    )
    r = rq.mappings().all()
    phone_data_df = pd.DataFrame(r)
    if len(phone_data_df) < 1:
        return {"": []}
    phone_data_df_by_date = (
        phone_data_df.groupby("date")
        .apply(lambda g: g.to_dict(orient="records"))
        .to_dict()
    )
    calls = {
        k.__str__(): [schemas.PhoneCall(**vv) for vv in v]
        for k, v in phone_data_df_by_date.items()
    }
    return calls


@router.get(
    "/{id}/stat",
    response_model=dict[str, list[schemas.DeviceUsage]]
                   | schemas.DeviceInternetActivity,
    description="`DeviceUsageAggregatedData.limit`, `DeviceUsageAggregatedData.today_exp` - random generated",
)
async def get_device_statistics(
    id: int,
    log_type: str = Query(schemas.LogTypeEnum.app.value, enum=schemas.log_type_values),
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    app_name: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    q = text(
        """
SELECT
    name,
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'week_day', week_day,
            'duration', duration,
            'duration_timestamp', duration_timestamp
        )
    ) AS usage_data_json,
    MAX(`date`) AS `date`
FROM (
    SELECT
        name,
        DAYOFWEEK(`date`) AS week_day,
        SEC_TO_TIME(SUM(`duration`)) AS duration,
        SUM(`duration`) AS duration_timestamp,
        `date`
    FROM
        kidl.logs l
    WHERE
        `log_type` = :log_type
        AND `device_id` = :device_id
        AND name != ""
        AND `date` BETWEEN :date_from AND :date_to
    GROUP BY
        name, DAYOFWEEK(`date`)
    ORDER BY
        name, week_day
) AS ordered_logs
GROUP BY
    name
ORDER BY
    `date` DESC;
        """
    )
    rq = await db.execute(
        q,
        {
            "device_id": id,
            "date_from": date_from.__str__(),
            "date_to": date_to.__str__(),
            "log_type": log_type,
        },
    )
    r = rq.mappings().all()
    df = pd.DataFrame(r)
    if app_name:
        df = df.loc[df["name"] == app_name]
    if len(df) < 1:
        return {"": []}

    stats = {}

    if log_type in ["url", "search_query"]:
        df_grouped = (
            df.groupby("name").apply(lambda g: g.to_dict(orient="records")).to_dict()
        )
        site_ratings = {}
        total_sites_count = 0
        total_sites_visit = 0
        total_duration = 0
        for k, v in df_grouped.items():
            for v2 in v:
                usage_data_json = json.loads(v2["usage_data_json"])
                sorted_usage_data = sorted(usage_data_json, key=lambda c: c["week_day"])
                visit_count = len(usage_data_json)

                durations = list(
                    map(
                        lambda c: c["duration_timestamp"],
                        sorted_usage_data,
                    )
                )
                duration = round(sum(durations), 0)
                total_sites_visit += visit_count
                total_duration += duration
                total_sites_count += 1
                site_ratings[k.__str__()] = schemas.DeviceInternetActivitySite(
                    visit_count=visit_count,
                    duration=duration,
                )
        agg_data = schemas.DeviceInternetActivityAggData(
            total_sites_count=total_sites_count,
            total_sites_visit=total_sites_visit,
            total_duration=total_duration,
        )
        stats = schemas.DeviceInternetActivity(
            usage_data=site_ratings, agg_data=agg_data
        )
    else:
        df_grouped = (
            df.groupby("date").apply(lambda g: g.to_dict(orient="records")).to_dict()
        )
        for k, v in df_grouped.items():
            device_usage_list = []
            for v2 in v:
                usage_data_json = json.loads(v2["usage_data_json"])
                sorted_usage_data = sorted(usage_data_json, key=lambda c: c["week_day"])

                durations = list(
                    map(
                        lambda c: c["duration_timestamp"],
                        sorted_usage_data,
                    )
                )
                avg_usage_seconds = sum(durations) // len(durations)
                today_exp = avg_usage_seconds * randint(2, 4)
                device_usage = schemas.DeviceUsage(
                    name=v2["name"],
                    usage_data=[
                        schemas.DeviceUsageData(**v3) for v3 in sorted_usage_data
                    ],
                    agg_data=schemas.DeviceUsageAggregatedData(
                        avg=avg_usage_seconds, today_exp=today_exp
                    ),
                )
                device_usage_list.append(device_usage)
            stats[k.__str__()] = device_usage_list
    return stats


async def get_devices_avatar(db: AsyncSession, ids: set[int]):
    q = select(DeviceTable.id, DeviceTable.avatar_url).filter(
        DeviceTable.id.in_(tuple(ids))
    )
    rq = await db.execute(q)
    r = [dict(x) for x in rq.mappings().all()]
    return r


@router.get(
    "/{id}/messages",
    response_model=dict[str, list[schemas.DeviceMessage]],
)
async def get_device_messages(
    id: int,
    message_type: Annotated[
        list[schemas.LogMessageEnum], Query(enum=schemas.sms_type_values)
    ],
    message_text_limit: int = 10,
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    log_type_f = []
    if len(message_type) > 0 and message_type[0].value == "all":
        log_type_f.extend(["in_sms", "out_sms"])
    else:
        log_type_f.extend([x.value for x in message_type])
    q = select(LogTable).filter(
        and_(
            LogTable.device_id == id,
            LogTable.log_type.in_(log_type_f),
        )
    )
    q = q.offset(offset).limit(limit)

    rq = await db.execute(q)
    r = rq.scalars().all()
    df = pd.DataFrame([schemas.PydanticLog(**x.__dict__).model_dump() for x in r])
    if len(df) < 1:
        return {"": []}
    df_by_date = (
        df.groupby("date").apply(lambda g: g.to_dict(orient="records")).to_dict()
    )
    devices_avatar = await get_devices_avatar(db=db, ids=set(df["device_id"].tolist()))
    messages = {
        k.__str__(): [
            schemas.DeviceMessage(
                avatar="".join(
                    list(
                        [
                            x["avatar_url"]
                            for x in filter(
                            lambda c: c["id"] == vv["device_id"], devices_avatar
                        )
                        ]
                    )
                ),
                name=vv["name"],
                text=" ".join(str(vv["title"]).split(" ")[:message_text_limit]),
                time=":".join(str(vv["time"]).split(":")[:2]),
                message_type=vv["log_type"],
            )
            for vv in v
        ]
        for k, v in df_by_date.items()
    }
    return messages


@router.get(
    "/conversation/{name}",
    response_model=schemas.Conversation | dict,
    description="`name` - Full text search",
)
async def get_conversation(
    name: str,
    *,
    message_type: Annotated[
        list[schemas.LogMessageEnum], Query(enum=schemas.sms_type_values)
    ],
    message_text_limit: int = 10,
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    log_type_f = []
    if len(message_type) > 0 and message_type[0].value == "all":
        log_type_f.extend(["in_sms", "out_sms"])
    else:
        log_type_f.extend([x.value for x in message_type])

    q = select(LogTable).filter(
        and_(
            LogTable.log_type.in_(log_type_f),
            LogTable.name.like(f"%{name}%"),
        )
    )
    q = q.offset(offset).limit(limit)
    rq = await db.execute(q)
    r = rq.scalars().all()
    df = pd.DataFrame([schemas.PydanticLog(**x.__dict__).model_dump() for x in r])
    if len(df) < 1:
        return {}
    df_by_date = (
        df.groupby("date").apply(lambda g: g.to_dict(orient="records")).to_dict()
    )
    devices_avatar = await get_devices_avatar(db=db, ids=set(df["device_id"].tolist()))
    messages = {
        k.__str__(): [
            schemas.DeviceMessage(
                avatar="".join(
                    list(
                        [
                            x["avatar_url"]
                            for x in filter(
                            lambda c: c["id"] == vv["device_id"], devices_avatar
                        )
                        ]
                    )
                ),
                name=vv["name"],
                text=" ".join(str(vv["title"]).split(" ")[:message_text_limit]) + "...",
                time=":".join(str(vv["time"]).split(":")[:2]),
                message_type=vv["log_type"],
            )
            for vv in v
        ]
        for k, v in df_by_date.items()
    }

    async def get_field_name():
        q = select(LogTable.name).filter(and_(LogTable.name.like(f"%{name}%"))).limit(1)
        rq = await db.execute(q)
        r = rq.scalars().first()
        return r

    db_name = await get_field_name()
    conversation = schemas.Conversation(
        phone_info=schemas.Phone(name=db_name), messages=messages
    )
    return conversation


async def _update_device(db: AsyncSession, id: int, model: schemas.PydanticDevice):
    q = select(DeviceTable).where(DeviceTable.id == id)
    rq = await db.execute(q)
    device = rq.scalars().first()
    if not device:
        raise HTTPException(status_code=status.HTTP_200_OK, detail="Not found")
    try:
        q_update = (
            update(DeviceTable)
            .where(DeviceTable.id == id)
            .values(
                **model.model_dump(
                    exclude_unset=True, exclude={"id", "wcSection_id", "member_id"}
                )
            )
        )
        await db.execute(q_update)
        await db.commit()
        await db.refresh(device)
        return device
    except SQLAlchemyError as e:
        logger.error(e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.__str__())


@router.put("/{id}", response_model=schemas.PydanticDevice)
async def update_device(
    id: int,
    data: schemas.PydanticDeviceUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    device = await _update_device(db=db, model=data, id=id)
    return device


@router.delete("/{id}")
async def delete_device(
    id: int,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(DeviceTable).where(DeviceTable.id == id)
    rq = await db.execute(q)
    device = rq.scalars().first()
    if not device:
        raise HTTPException(status_code=status.HTTP_200_OK, detail="Not found")
    bucket_name = DeviceTable.__name__
    with suppress(Exception):
        async with create_storage_client() as storage_client:
            await storage_client.delete_object(
                Bucket=bucket_name,
                Key=device.avatar_url,
            )
    try:
        q_delete = delete(DeviceTable).where(DeviceTable.id == id)
        await db.execute(q_delete)
        await db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.__str__())


@router.post("/{id}/upload-avatar/", response_model=schemas.PydanticDevice)
async def upload_device_avatar(
    request: Request,
    id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
):
    q = select(DeviceTable).filter(
        and_(
            DeviceTable.id == id,
        )
    )
    rq = await db.execute(q)
    device = rq.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    file_extension = file.filename.split(".")[-1]
    bucket_name = DeviceTable.__name__
    async with create_storage_client() as storage_client:
        if bucket_name not in request.app.state.storage_bucket_names:
            await storage_client.create_bucket(Bucket=bucket_name, ACL="public-read")
        url = await upload_file_to_storage(
            s3_client=storage_client,
            file=file.file,
            file_extension=file_extension,
            bucket_name=bucket_name,
        )
    try:
        assert url is not None, "url is None"
        device.avatar_url = url
        db.add(device)
        await db.commit()
        await db.refresh(device)
    except SQLAlchemyError as e:
        logger.error(e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.__str__())
    return schemas.PydanticDevice(**device.__dict__)
