import re
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from deps import CurrentUser, DbSession
from models import Organization, User
from schemas import TokenResponse, UserLogin, UserOut, UserRegister
from services.audit import log_audit
from services.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister, db: DbSession):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    slug_base = _slugify(data.organization_name)
    slug = slug_base
    counter = 1
    while True:
        org_check = await db.execute(select(Organization).where(Organization.slug == slug))
        if not org_check.scalar_one_or_none():
            break
        slug = f"{slug_base}-{counter}"
        counter += 1

    org = Organization(name=data.organization_name, slug=slug)
    db.add(org)
    await db.flush()

    user = User(
        organization_id=org.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.flush()

    await log_audit(db, org.id, user.id, "register", "user", str(user.id))
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(str(user.id), str(org.id)),
        refresh_token=create_refresh_token(str(user.id), str(org.id)),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: DbSession):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    await log_audit(db, user.organization_id, user.id, "login", "user", str(user.id))
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.organization_id)),
        refresh_token=create_refresh_token(str(user.id), str(user.organization_id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: DbSession):
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user_id = uuid.UUID(payload["sub"])
        org_id = uuid.UUID(payload["org_id"])
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(str(user_id), str(org_id)),
        refresh_token=create_refresh_token(str(user_id), str(org_id)),
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
