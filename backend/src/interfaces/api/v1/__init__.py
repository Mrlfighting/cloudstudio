from fastapi import APIRouter

from ....infrastructure.auth.routes import router as auth_router
from ....modules.analytics.routes import router as analytics_router
from ....modules.api_keys.routes import router as api_keys_router
from ....modules.pictures.routes import router as pictures_router
from ....modules.rate_limit.routes import router as rate_limits_router
from ....modules.space.routes import router as spaces_router
from ....modules.tier.routes import router as tiers_router
from ....modules.user.routes import router as users_router
from .cache import router as cache_router

router = APIRouter(prefix="/v1")
router.include_router(users_router, prefix="/users")
router.include_router(tiers_router, prefix="/tiers")
router.include_router(rate_limits_router, prefix="/rate-limits")
router.include_router(auth_router, prefix="/auth")
router.include_router(api_keys_router, prefix="/api-keys")
router.include_router(pictures_router, prefix="/pictures")
router.include_router(spaces_router, prefix="/spaces")
router.include_router(analytics_router, prefix="/analytics")
router.include_router(cache_router, prefix="/cache")
