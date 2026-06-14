"""
NEXUS — Authentication Layer
Google OAuth2 (primary) + GitHub OAuth2 (secondary/connections)
JWT sessions stored server-side in DB. No localStorage on client.
"""
import uuid
import httpx
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.config import settings
from core.database import get_db, User, GitHubConnection

bearer_scheme = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"

# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# ── Current User ──────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = decode_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# ── Google OAuth ──────────────────────────────────────────────────────────────

GOOGLE_TOKEN_URL   = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


async def exchange_google_code(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        r.raise_for_status()
        token_data = r.json()

        info = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        info.raise_for_status()
        return info.json()


async def upsert_google_user(db: AsyncSession, google_info: dict) -> User:
    email = google_info["email"]
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=google_info.get("name", email),
            photo_url=google_info.get("picture"),
            auth_provider="google",
        )
        db.add(user)
    else:
        # Update photo/name if changed
        user.photo_url = google_info.get("picture", user.photo_url)
        user.name = google_info.get("name", user.name)
        user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user)
    return user


# ── GitHub OAuth ──────────────────────────────────────────────────────────────

GITHUB_TOKEN_URL   = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"


async def exchange_github_code(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        token_data = r.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, "GitHub OAuth failed: no access_token")

        info = await client.get(
            GITHUB_USERINFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        info.raise_for_status()
        user_info = info.json()
        user_info["_access_token"] = access_token
        return user_info


async def upsert_github_login_user(db: AsyncSession, gh_info: dict) -> User:
    """Used when someone logs in DIRECTLY with GitHub (not connecting to existing account)."""
    github_email = gh_info.get("email") or f"{gh_info['login']}@github.noemail"
    result = await db.execute(select(User).where(User.email == github_email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=github_email,
            name=gh_info.get("name") or gh_info["login"],
            photo_url=gh_info.get("avatar_url"),
            auth_provider="github",
        )
        db.add(user)
        await db.flush()

    # Always upsert the GitHub connection
    await upsert_github_connection(db, user.id, gh_info)
    await db.commit()
    await db.refresh(user)
    return user


async def upsert_github_connection(
    db: AsyncSession, user_id: str, gh_info: dict
) -> GitHubConnection:
    """Connect a GitHub account to an existing user (multi-GitHub support)."""
    github_user_id = str(gh_info["id"])
    result = await db.execute(
        select(GitHubConnection).where(
            GitHubConnection.user_id == user_id,
            GitHubConnection.github_user_id == github_user_id,
        )
    )
    conn = result.scalar_one_or_none()

    if not conn:
        # Check if this is first connection → make it primary
        existing = await db.execute(
            select(GitHubConnection).where(GitHubConnection.user_id == user_id)
        )
        is_first = existing.scalar_one_or_none() is None

        conn = GitHubConnection(
            id=str(uuid.uuid4()),
            user_id=user_id,
            github_username=gh_info["login"],
            github_user_id=github_user_id,
            access_token=gh_info["_access_token"],
            avatar_url=gh_info.get("avatar_url"),
            is_primary=is_first,
        )
        db.add(conn)
    else:
        conn.access_token = gh_info["_access_token"]
        conn.avatar_url = gh_info.get("avatar_url")
        conn.github_username = gh_info["login"]

    await db.flush()
    return conn