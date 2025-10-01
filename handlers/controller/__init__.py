from aiogram import Router

from . import (
    connection_service,
    export,
    inbox,
    language,
    monitoring,
    orders,
    realtime_monitoring,
    technical_service,
    technicians,
)

router = Router()

router.include_routers(
    connection_service.router,
    export.router,
    inbox.router,
    language.router,
    monitoring.router,
    orders.router,
    realtime_monitoring.router,
    technical_service.router,
    technicians.router,
)
