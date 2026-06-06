from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from config import settings

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    model_config = ConfigDict(strict=True)

    status: str        # "ok" | "degraded"
    environment: str
    redis: str         # "ok" | "unreachable"


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Deep health check — verifies Redis connectivity."""
    redis_status = await _ping_redis()
    return HealthStatus(
        status="ok" if redis_status == "ok" else "degraded",
        environment=settings.environment,
        redis=redis_status,
    )


async def _ping_redis() -> str:
    try:
        import redis.asyncio as aioredis  # noqa: PLC0415
        r: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
            settings.redis_url, decode_responses=True
        )
        await r.ping()
        await r.aclose()
        return "ok"
    except Exception:
        return "unreachable"
