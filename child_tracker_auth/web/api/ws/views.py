import asyncio
import json
from contextlib import suppress
from typing import Annotated

from fastapi import WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.params import Query
from loguru import logger
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import select, and_
from starlette import status
from starlette.websockets import WebSocket

from child_tracker_auth import schemas
from child_tracker_auth.db.base import DeviceTable
from child_tracker_auth.security.oauth2 import verify_access_token
from child_tracker_auth.web.lifespan import create_session_factory, redis_client


class WebsocketConnectionManager:
    def __init__(self, redis_client: Redis):
        self.active_connections: dict[str, WebSocket] = {}
        self.redis_client = redis_client

    async def connect(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        await self.redis_client.sadd("active_connections", device_id)

    async def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
        await self.redis_client.srem("active_connections", device_id)

    async def send_personal_message(self, message: str, device_id: str):
        websocket: WebSocket = self.active_connections.get(device_id)
        if websocket:
            await websocket.send_text(message)

    def get_active_connections(self):
        return self.redis_client.smembers("active_connections")


websocket_connection_manager = WebsocketConnectionManager(redis_client)

router = APIRouter()
engine, session_factory = create_session_factory()


@router.websocket("/parent/children_device/{device_id}/geo/")
async def parent_websocket_endpoint(
    websocket: WebSocket,
    access_token: Annotated[str, Query(...)],
    device_id: str
):
    credentials_exception = WebSocketException(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="Could not validate credentials",
    )
    parent_member = verify_access_token(access_token, credentials_exception)

    await websocket.accept()

    try:
        pubsub = redis_client.pubsub()

        key = f"device_id:{device_id}:member_id:{parent_member.user_id}"

        await pubsub.subscribe(key)
        async for message in pubsub.listen():
            logger.debug(message)
            with suppress(TypeError):
                if message:
                    data = message['data']
                    assert json.loads(data)
                    await websocket.send_bytes(data)
    except asyncio.TimeoutError:
        logger.info("WebSocket connection timed out")
        await websocket.close(
            code=status.WS_1001_GOING_AWAY, reason="Connection timed out"
        )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


@router.websocket("/children/device/{device_id}/geo")
async def children_websocket_endpoint(websocket: WebSocket, device_id: str):
    async with session_factory() as db:
        q = select(DeviceTable).where(
            and_(
                DeviceTable.id == int(device_id),
            )
        )
        rq = await db.execute(q)
        device_obj = rq.scalars().first()
        if not device_obj:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="No authorized devices found",
            )
            return

    await websocket_connection_manager.connect(websocket, device_obj.id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                geolocation_message = schemas.GeolocationMessage.model_validate_json(
                    data
                )

                key = f"device_id:{device_obj.id}:member_id:{device_obj.member_id}"

                await redis_client.publish(
                    key,
                    geolocation_message.model_dump_json(),
                )

                await redis_client.geoadd(
                    key,
                    values=[
                        geolocation_message.longitude,
                        geolocation_message.latitude,
                        device_id,
                    ],
                )
            except (ValueError, TypeError, AssertionError, ValidationError) as e:
                logger.error(f"Validation error: {e}")
                await websocket.send_text(json.dumps({"error": str(e)}))

    except asyncio.TimeoutError:
        logger.info("WebSocket connection timed out")
        await websocket.close(
            code=status.WS_1001_GOING_AWAY, reason="Connection timed out"
        )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    finally:
        await websocket_connection_manager.disconnect(device_obj.id)
