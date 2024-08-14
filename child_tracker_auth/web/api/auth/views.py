from fastapi import APIRouter, BackgroundTasks
from fastapi import Depends, HTTPException, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.requests import Request

import schemas
from child_tracker_auth.security.oauth2 import create_access_token
from db.base import MemberTable
from db.dependencies import get_db_session
from security.crypto import get_password_hashed
from security.token import generate_token, verify_token
from settings import settings
from utils.email import send_email_async

router = APIRouter()


@router.post(
    "/register/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.RegistrationUserRepsonse,
)
async def register(
    request: Request,
    user_credentials: schemas.PydanticMemberCreate,
    db: AsyncSession = Depends(get_db_session),
    *,
    background_tasks: BackgroundTasks,
):
    # Check if email already exists
    email_check_query = select(MemberTable).filter(
        MemberTable.email == user_credentials.email
    )
    email_check_result = await db.execute(email_check_query)
    email_check = email_check_result.scalars().first()

    if email_check is not None:
        raise HTTPException(
            detail="Email is already registered", status_code=status.HTTP_409_CONFLICT
        )

    # Hash the password
    hashed_password = get_password_hashed(user_credentials.password)
    user_credentials.password = hashed_password

    new_user = MemberTable(
        email=user_credentials.email,
        name=user_credentials.name,
        role=user_credentials.role,
        active=user_credentials.active,
        password="",
        password_pbkdf_hash=user_credentials.password,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    if not user_credentials.active:
        token = generate_token(user_credentials.email)
        email_verification_endpoint = f"{settings.frontend_url}/confirm-email/{token}/"
        mail_body = {
            "email": user_credentials.email,
            "project_name": settings.project_name,
            "url": email_verification_endpoint,
        }

        background_tasks.add_task(
            send_email_async,
            **dict(
                subject="Email Verification: Registration Confirmation",
                email_to=user_credentials.email,
                body=mail_body,
                template="email_verification.html",
            ),
        )

    new_user_response = schemas.RegistrationUserRepsonse(
        message="User registration successful",
        data=schemas.PydanticMember(**new_user.__dict__),
    )
    return new_user_response


@router.post("/login/", status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
):
    # Filter search for user
    user_query = select(MemberTable).filter(
        MemberTable.email == user_credentials.username
    )
    user_result = await db.execute(user_query)
    user = user_result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Username or Password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Account Not Verified"
        )

    access_token = create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/confirm-email/{token}/", status_code=status.HTTP_202_ACCEPTED)
async def user_verification(token: str, db: AsyncSession = Depends(get_db_session)):
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Token for Email Verification has expired.",
        )

    user_query = select(MemberTable).filter(MemberTable.email == token_data["email"])
    user_result = await db.execute(user_query)
    user = user_result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {token_data['email']} does not exist",
        )
    user.active = 1
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "message": "Email Verification Successful",
        "status": status.HTTP_202_ACCEPTED,
    }


@router.post("/resend-verification/", status_code=status.HTTP_201_CREATED)
async def send_email_verfication(
    email_data: schemas.EmailSchema,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    *,
    background_tasks: BackgroundTasks,
):
    user_check_query = select(MemberTable).filter(MemberTable.email == email_data.email)
    user_check_result = await db.execute(user_check_query)
    user_check = user_check_result.scalars().first()

    if not user_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User information does not exist",
        )

    token = generate_token(email_data.email)
    email_verification_endpoint = f"{settings.frontend_url}auth/confirm-email/{token}/"
    mail_body = {
        "email": user_check.email,
        "project_name": settings.project_name,
        "url": email_verification_endpoint,
    }

    background_tasks.add_task(
        send_email_async,
        **dict(
            subject="Email Verification: Registration Confirmation",
            email_to=user_check.email,
            body=mail_body,
            template="email_verification.html",
        ),
    )
