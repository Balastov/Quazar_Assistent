from fastapi import APIRouter
from sqlalchemy import select

from deps import CurrentUser, DbSession
from models import AuditLog
from schemas import AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(user: CurrentUser, db: DbSession, limit: int = 100):
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == user.organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 500))
    )
    return result.scalars().all()
