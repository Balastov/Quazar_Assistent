from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from deps import CurrentUser, DbSession
from models import LlmUsageEvent
from packages.llm_providers.router import LLMRouter
from schemas import LlmModelOut, UsageSummary

router = APIRouter(prefix="/llm", tags=["llm"])
llm_router = LLMRouter()


@router.get("/models", response_model=list[LlmModelOut])
async def list_models():
    models = llm_router.list_models()
    return [
        LlmModelOut(
            id=m["id"],
            provider=m["provider"],
            display_name=m["display_name"],
            context_window=m["context_window"],
            supports_vision=False,
        )
        for m in models
    ]


@router.get("/usage", response_model=UsageSummary)
async def usage_summary(user: CurrentUser, db: DbSession, days: int = 30):
    since = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(
            LlmUsageEvent.model_id,
            func.sum(LlmUsageEvent.prompt_tokens).label("prompt_tokens"),
            func.sum(LlmUsageEvent.completion_tokens).label("completion_tokens"),
            func.sum(LlmUsageEvent.estimated_cost).label("cost"),
        )
        .where(
            LlmUsageEvent.organization_id == user.organization_id,
            LlmUsageEvent.created_at >= since,
        )
        .group_by(LlmUsageEvent.model_id)
    )
    rows = result.all()

    total_prompt = 0
    total_completion = 0
    total_cost = 0.0
    by_model = {}

    for row in rows:
        prompt = int(row.prompt_tokens or 0)
        completion = int(row.completion_tokens or 0)
        cost = float(row.cost or 0)
        total_prompt += prompt
        total_completion += completion
        total_cost += cost
        by_model[row.model_id] = {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "estimated_cost": cost,
        }

    return UsageSummary(
        total_prompt_tokens=total_prompt,
        total_completion_tokens=total_completion,
        estimated_cost=total_cost,
        by_model=by_model,
    )
