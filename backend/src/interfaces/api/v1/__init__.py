from fastapi import APIRouter, Depends

from ....infrastructure.auth.routes import router as auth_router
from ....infrastructure.rate_limit.middleware import check_rate_limit
from ....modules.analytics.routes import router as analytics_router
from ....modules.api_keys.routes import router as api_keys_router
from ....modules.bead_pattern.routes import router as bead_pattern_router
from ....modules.email_verification.routes import router as email_router
from ....modules.pictures.routes import router as pictures_router
from ....modules.rate_limit.routes import router as rate_limits_router
from ....modules.space.collab import router as space_collab_router
from ....modules.space.routes import router as spaces_router
from ....modules.tier.routes import router as tiers_router
from ....modules.user.routes import router as users_router
from .cache import router as cache_router

router = APIRouter(prefix="/v1")
# HTTP 依赖不能附加到 WebSocket，后者独立执行会话、Origin 与消息限流。
router.include_router(email_router, prefix="/email", dependencies=[Depends(check_rate_limit)])
router.include_router(bead_pattern_router, prefix="/bead-patterns", dependencies=[Depends(check_rate_limit)])
router.include_router(users_router, prefix="/users", dependencies=[Depends(check_rate_limit)])
router.include_router(tiers_router, prefix="/tiers", dependencies=[Depends(check_rate_limit)])
router.include_router(rate_limits_router, prefix="/rate-limits", dependencies=[Depends(check_rate_limit)])
router.include_router(auth_router, prefix="/auth", dependencies=[Depends(check_rate_limit)])
router.include_router(api_keys_router, prefix="/api-keys", dependencies=[Depends(check_rate_limit)])
router.include_router(pictures_router, prefix="/pictures", dependencies=[Depends(check_rate_limit)])
router.include_router(spaces_router, prefix="/spaces", dependencies=[Depends(check_rate_limit)])
router.include_router(space_collab_router, prefix="/spaces")
router.include_router(analytics_router, prefix="/analytics", dependencies=[Depends(check_rate_limit)])
router.include_router(cache_router, prefix="/cache", dependencies=[Depends(check_rate_limit)])
