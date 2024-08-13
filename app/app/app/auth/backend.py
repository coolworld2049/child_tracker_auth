from fastapi_users.authentication import AuthenticationBackend

from app.auth.transport import bearer_transport
from app.auth.jwt import get_jwt_strategy

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
