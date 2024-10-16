import asyncio
import json
from contextlib import suppress

from cashews import cache
from fastapi import WebSocketDisconnect, APIRouter
from geopy.distance import geodesic
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette import status
from starlette.websockets import WebSocket

from child_tracker_auth import schemas
from child_tracker_auth.db.base import LogTable, DeviceTable
from child_tracker_auth.settings import settings
from child_tracker_auth.web.lifespan import create_session_factory, ws_redis_client

router = APIRouter(prefix=f"/{settings.websocket_secret_key}")
engine, session_factory = create_session_factory()

# Set a minimum movement distance before logging
MIN_DISTANCE_METERS = 5
# Set batch size for logs before committing to the database
BATCH_SIZE = 5


@router.websocket("/parent/children_device/{dsn}/geo/")
async def parent_websocket_endpoint(websocket: WebSocket, dsn: str):
    key = f"device_dsn:{dsn}"
    await websocket.accept()

    pubsub = ws_redis_client.pubsub()
    await pubsub.subscribe(key)

    try:
        async for message in pubsub.listen():
            with suppress(TypeError, json.JSONDecodeError):
                data = message["data"]
                logger.debug(
                    f"channel: {bytes(message['channel']).decode()} data: {bytes(data).decode()}"
                )
                await websocket.send_bytes(data)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except asyncio.TimeoutError:
        logger.info("WebSocket connection timed out")
        await websocket.close(
            code=status.WS_1001_GOING_AWAY, reason="Connection timed out"
        )
    finally:
        await pubsub.unsubscribe(key)
        await websocket.close()


@cache(ttl="1d", key="get_device_id:device_dsn:{dsn}")
async def get_device_id(dsn: str):
    async with session_factory() as db:
        try:
            result = await db.execute(
                select(DeviceTable.id).filter(DeviceTable.dsn == dsn)
            )
            return result.scalar()
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch device ID for {dsn}: {e}")
            return None


@router.websocket("/children/device/{dsn}/geo/")
async def children_websocket_endpoint(websocket: WebSocket, dsn: str):
    channel = f"device_dsn:{dsn}"
    last_position: tuple[float, float] | None = None
    geo_logs_batch = []

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                geo_msg = schemas.GeolocationMessage.model_validate_json(data)
                assert -90 <= geo_msg.latitude <= 90, "Invalid latitude"
                assert -180 <= geo_msg.longitude <= 180, "Invalid longitude"

                logger.debug(f"Received data on {channel}: {data}")

                # Publish to Redis channel
                await ws_redis_client.publish(channel, geo_msg.model_dump_json())

                current_position = (geo_msg.latitude, geo_msg.longitude)
                if last_position:
                    distance = geodesic(last_position, current_position).meters
                    if distance >= MIN_DISTANCE_METERS:
                        device_id = await get_device_id(dsn)
                        if device_id:
                            geo_logs_batch.append(
                                LogTable(
                                    device_id=device_id,
                                    log_type="gps-point",
                                    name=",".join(map(str, current_position)),
                                    date=geo_msg.device_date.date(),
                                    time=geo_msg.device_date.time(),
                                )
                            )
                            logger.info(f"Device {dsn} moved {distance:.2f} meters")

                            # Commit logs in batches
                            if len(geo_logs_batch) >= BATCH_SIZE:
                                await save_logs(geo_logs_batch)
                                logger.info(
                                    f"The history of movements from {BATCH_SIZE} points is recorded in the database"
                                )
                                geo_logs_batch = []

                last_position = current_position

                # Slightly reduced sleep for more responsiveness
                await asyncio.sleep(0.05)

            except (ValueError, TypeError, AssertionError, ValidationError) as e:
                logger.error(f"Validation error: {e}")
                await websocket.send_text(json.dumps({"error": str(e)}))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except asyncio.TimeoutError:
        logger.info("WebSocket connection timed out")
        await websocket.close(
            code=status.WS_1001_GOING_AWAY, reason="Connection timed out"
        )
    finally:
        if geo_logs_batch:
            await save_logs(geo_logs_batch)  # Save remaining logs before closing
        await websocket.close()


async def save_logs(logs):
    async with session_factory() as db:
        try:
            db.add_all(logs)
            await db.commit()
            logger.debug(f"Committed {len(logs)} logs to the database")
        except SQLAlchemyError as e:
            logger.error(f"Failed to save logs: {e}")
            await db.rollback()
