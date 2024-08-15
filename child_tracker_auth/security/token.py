import binascii

from itsdangerous import URLSafeTimedSerializer, BadTimeSignature, SignatureExpired
from jose import jwt, JWTError
from pydantic import EmailStr

from child_tracker_auth.settings import settings

token_algo = URLSafeTimedSerializer(
    settings.secret_key, salt="Email_Verification_&_Forgot_password"
)


def generate_token(email: EmailStr) -> str:
    _token = token_algo.dumps(email)
    hex_token = binascii.hexlify(_token.encode()).decode()
    return hex_token


def verify_token(hex_token: str):
    try:
        _token = binascii.unhexlify(hex_token.encode()).decode()
        email = token_algo.loads(_token, max_age=1800)
    except (SignatureExpired, BadTimeSignature, binascii.Error):
        return None
    return {"email": email, "check": True}


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id: str = payload.get("user_id")
        if user_id is None:
            return None
        return payload
    except JWTError:
        return None
