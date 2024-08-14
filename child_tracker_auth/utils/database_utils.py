from passlib.context import CryptContext
from passlib.hash import pbkdf2_sha256

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pbkdf2_sha256.verify(plain_password, hashed_password)


def get_password_hashed(password):
    return pbkdf2_sha256.hash(password)
