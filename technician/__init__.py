from aiogram import Router

from . import (
    inbox,
    connection_inbox,
    technician_orders,
    staff_inbox,
    materials_flow,
    reports,
    language,
)

router = Router()

router.include_routers(
    inbox.router,
    connection_inbox.router,
    technician_orders.router,
    staff_inbox.router,
    materials_flow.router,
    reports.router,
    language.router,
)
