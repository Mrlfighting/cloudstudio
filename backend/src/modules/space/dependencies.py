from typing import Annotated

from fastapi import Depends

from .service import SpaceService


def get_space_service() -> SpaceService:
    return SpaceService()


SpaceServiceDep = Annotated[SpaceService, Depends(get_space_service)]
