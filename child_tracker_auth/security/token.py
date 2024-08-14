from itsdangerous import URLSafeTimedSerializer, BadTimeSignature, SignatureExpired
from jose import jwt, JWTError
from pydantic import EmailStr

from settings import settings

token_algo = URLSafeTimedSerializer(
    settings.secret_key, salt="Email_Verification_&_Forgot_password"
)


def generate_token(email: EmailStr):
    _token = token_algo.dumps(email)
    return _token


def verify_token(token: str):
    try:
        email = token_algo.loads(token, max_age=1800)
    except SignatureExpired:
        return None
    except BadTimeSignature:
        return None
    return {"email": email, "check": True}


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, settings.secret_key,
                             algorithms=[settings.algorithm])
        user_id: str = payload.get("user_id")
        if user_id is None:
            return None
        return payload
    except JWTError:
        return None
