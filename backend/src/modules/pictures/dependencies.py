from typing import Annotated

from fastapi import Depends

from .service import PictureService


def get_picture_service() -> PictureService:
    return PictureService()


PictureServiceDep = Annotated[PictureService, Depends(get_picture_service)]
