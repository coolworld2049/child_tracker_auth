from loguru import logger
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class HTTPErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception as e:
            err = dict(
                type=e.__class__.__name__,
                message=str(e),
                detail="\n".join([str(x) for x in e.args]),
            )
            logger.exception(e)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=err,
            )
        return response
