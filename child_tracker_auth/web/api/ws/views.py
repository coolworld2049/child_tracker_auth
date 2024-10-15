import asyncio
import json
from contextlib import suppress

from fastapi import WebSocketDisconnect, APIRouter
from loguru import logger
from pydantic import ValidationError
from redis.asyncio import Redis
from starlette import status
from starlette.websockets import WebSocket

from child_tracker_auth import schemas
from child_tracker_auth.settings import settings
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

router = APIRouter(prefix=f"/{settings.websocket_secret_key}")
engine, session_factory = create_session_factory()


@router.websocket("/parent/children_device/{dsn}/geo/")
async def parent_websocket_endpoint(
    websocket: WebSocket,
    dsn: str
):
    """
    device_dsn: [].dsn из из тела ответа эндпоинта GET /api/members/me/devices
    """
    key = f"device_dsn:{dsn}"

    try:
        await websocket.accept()

        pubsub = redis_client.pubsub()

        await pubsub.subscribe(key)

        async for message in pubsub.listen():
            logger.debug(f"channel: {bytes(message['channel']).decode()} data: {bytes(message['data']).decode()}")
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


@router.websocket("/children/device/{dsn}/geo/")
async def children_websocket_endpoint(websocket: WebSocket, dsn: str):
    """
    device_dsn: [].dsn из из тела ответа эндпоинта GET /api/members/me/devices
    """

    channel = f"device_dsn:{dsn}"

    try:
        await websocket_connection_manager.connect(websocket, dsn)

        while True:
            try:
                data = await websocket.receive_text()
                geolocation_message = schemas.GeolocationMessage.model_validate_json(
                    data
                )

                logger.debug(f"channel: {channel} data: {data}")
                await redis_client.publish(
                    channel,
                    geolocation_message.model_dump_json(),
                )

                await redis_client.geoadd(
                    channel,
                    values=[
                        geolocation_message.longitude,
                        geolocation_message.latitude,
                        dsn,
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
        await websocket_connection_manager.disconnect(dsn)
