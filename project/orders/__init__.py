from fastapi import APIRouter

orders_router = APIRouter(
    prefix="/order",
)

from . import models  # noqa
