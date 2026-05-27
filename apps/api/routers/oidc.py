"""OIDC authentication endpoints (optional, enterprise phase)."""

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth/oidc", tags=["oidc"])


@router.get("/login")
async def oidc_login(request: Request):
    if not settings.oidc_enabled:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="OIDC is not enabled")

    from authlib.integrations.starlette_client import OAuth

    oauth = OAuth()
    oauth.register(
        name="oidc",
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        server_metadata_url=f"{settings.oidc_issuer}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    redirect_uri = str(request.url_for("oidc_callback"))
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def oidc_callback(request: Request):
    if not settings.oidc_enabled:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="OIDC is not enabled")

    # Full user provisioning flow would map OIDC claims to User/Organization records.
    # Stub redirects to web app after successful auth in production setup.
    return RedirectResponse(url=f"{settings.web_url}/?oidc=success")
