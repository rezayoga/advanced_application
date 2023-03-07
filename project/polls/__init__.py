from fastapi import APIRouter

polls_router = APIRouter(
    prefix="/poll",
)

from . import models  # noqa
