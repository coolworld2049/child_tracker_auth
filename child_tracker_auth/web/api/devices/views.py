import collections
import json
import pathlib
from datetime import date
from random import randint

import pandas as pd
from fastapi import APIRouter
from fastapi.params import Depends, Query
from mimesis import Internet
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from child_tracker_auth import schemas
from child_tracker_auth.db.base import LogTable, FileTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.schemas import log_type_values
from child_tracker_auth.security.oauth2 import get_current_member
from child_tracker_auth.settings import settings
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


@router.get("/{id}/files", response_model=list[schemas.PydanticFile])
async def get_device_files(
    id: int,
    offset: int = 0,
    limit: int = 100,
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(FileTable).filter(
        and_(FileTable.device_id == id, FileTable.time.between(date_from, date_to))
    )
    q = q.offset(offset).limit(limit)
    rq = await db.execute(q)
    r = rq.scalars().all()
    logs = [schemas.PydanticFile(**x.__dict__) for x in r]
    return logs


@router.get("/{id}/file/{file_id}", response_class=FileResponse)
async def download_device_files(
    id: int,
    file_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(FileTable).filter(
        and_(FileTable.id == file_id, FileTable.device_id == id)
    )
    rq = await db.execute(q)
    r = rq.scalars().first()
    m = schemas.PydanticFile(**r.__dict__)
    file_path = pathlib.Path(settings.public_dir_path).parent.joinpath(
        str(m.path).lstrip("/")
    )
    return FileResponse(file_path, media_type=m.type, filename=m.name)


@router.get(
    "/{id}/phone_book",
    response_model=dict[str, list[schemas.PhoneBookItem]],
    description="dict key - uppercase alphabetic letter",
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
    join devices d on
        d.id = l.device_id
    where
        d.id = :device_id
        and l.log_type in ('in_call', 'out_call', 'out_sms')
    group by l.name
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
    r = rq.mappings().all()
    df = pd.DataFrame(r)

    if len(df) < 1:
        return {"": []}

    def process_raw_name(s: pd.Series):
        """
        :returns: dict[name, phone]
        """
        return {
            str(x.split(" ")[1]): x.split(" ")[0] for x in s if len(x.split(" ")) == 2
        }

    name_phone_dict: dict = df.apply(process_raw_name).tolist()[0]
    phone_book_dict: dict[str, list[schemas.PhoneBookItem]] = collections.defaultdict(
        list
    )
    for name, phone in name_phone_dict.items():
        key = name[0].lower()
        phone_book_dict[key].append(schemas.PhoneBookItem(name=name, phone=phone))

    phone_book = dict(sorted(phone_book_dict.items(), key=lambda c: c[0]))
    return phone_book


@router.get(
    "/{id}/calls",
    response_model=dict[str, list[schemas.PhoneCall]],
    description="dict key - date e.g 2024-08-22",
)
async def get_device_calls(
    id: int,
    offset: int = 0,
    limit: int = 100,
    date_from: date = date_from_default,
    date_to: date = date_to_default,
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
    and (l.`date` between :date_from and :date_to)
limit :limit OFFSET :offset
    """
    )
    rq = await db.execute(
        q,
        {
            "limit": limit,
            "offset": offset,
            "device_id": id,
            "date_from": date_from.__str__(),
            "date_to": date_to.__str__(),
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
    response_model=dict[str, list[schemas.DeviceUsage]],
)
async def get_device_statistics(
    id: int,
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
            'hour', hour,
            'duration', duration
        )
    ) AS usage_data_json,
    MAX(`date`) AS `date`
FROM (
    SELECT
        name,
        DAYOFWEEK(`date`) AS week_day,
        HOUR(`time`) AS hour,
        SUM(`duration`) AS duration,
        `date`
    FROM
        kidl.logs l
    WHERE
        `log_type` = 'app'
        AND `device_id` = :device_id
        AND name != ""
        AND `date` BETWEEN :date_from AND :date_to
    GROUP BY
        name, DAYOFWEEK(`date`), HOUR(`time`)
    ORDER BY
        name, week_day, hour
) AS ordered_logs
GROUP BY
    name
ORDER BY
    `date`;
        """
    )
    rq = await db.execute(
        q,
        {
            "device_id": id,
            "date_from": date_from.__str__(),
            "date_to": date_to.__str__(),
        },
    )
    r = rq.mappings().all()
    df = pd.DataFrame(r)
    if app_name:
        df = df.loc[df["name"] == app_name]
    if len(df) < 1:
        return {"": []}

    df_grouped = (
        df.groupby("date").apply(lambda g: g.to_dict(orient="records")).to_dict()
    )

    stats = {}
    for k, v in df_grouped.items():
        device_usage_list = []
        for v2 in v:
            usage_data_json = json.loads(v2["usage_data_json"])
            sorted_usage_data = sorted(usage_data_json, key=lambda c: c["week_day"])

            durations = list(
                map(
                    lambda c: c["duration"],
                    sorted_usage_data,
                )
            )
            avg_usage_seconds = sum(durations) // len(durations)
            today_exp = avg_usage_seconds * randint(2, 4)
            device_usage = schemas.DeviceUsage(
                name=v2["name"],
                usage_data=[schemas.DeviceUsageData(**v3) for v3 in sorted_usage_data],
                agg_data=schemas.DeviceUsageAggregatedData(
                    avg=avg_usage_seconds, today_exp=today_exp
                ),
            )
            device_usage_list.append(device_usage)
        stats[k.__str__()] = device_usage_list
    return stats


@router.get(
    "/{id}/messages/incoming",
    response_model=dict[str, list[schemas.DeviceMessageIncoming]],
)
async def get_device_incoming_sms_list(
    id: int,
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(LogTable).filter(
        and_(
            LogTable.device_id == id,
            LogTable.log_type == "in_sms",
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
    messages = {
        k.__str__(): [
            schemas.DeviceMessageIncoming(
                avatar=internet.stock_image_url(keywords=["people"]),
                name=vv["name"],
                text=" ".join(str(vv["title"]).split(" ")[:3]) + "...",
                time=":".join(str(vv["time"]).split(":")[:2]),
            )
            for vv in v
        ]
        for k, v in df_by_date.items()
    }
    return messages
