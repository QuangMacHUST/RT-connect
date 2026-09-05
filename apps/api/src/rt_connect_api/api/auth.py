"""P2 session verification endpoint; no passwords or service credentials pass through it."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity

router = APIRouter(prefix="/auth", tags=["auth"])


class SessionIdentityResponse(BaseModel):
    subject: str
    email: str | None


@router.get("/session", response_model=SessionIdentityResponse)
def session(
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
) -> SessionIdentityResponse:
    return SessionIdentityResponse(subject=identity.subject, email=identity.email)
