import logging
from django.db import transaction
from asgiref.sync import sync_to_async
from .models import User, UserRole

logger = logging.getLogger("apps.bot")

@sync_to_async
def get_or_create_user_by_telegram(
    telegram_id: int,
    username: str = "",
    full_name: str = "",
) -> tuple[User, bool]:
    user = User.objects.filter(telegram_id=telegram_id).select_related("department").first()
    if user:
        changed = False
        if username and user.username != username and not User.objects.filter(username=username).exclude(pk=user.pk).exists():
            user.username = username
            changed = True
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            user.save(update_fields=["username", "full_name", "updated_at"])
        return user, False

    base_username = username or f"tg_{telegram_id}"
    final_username = base_username
    counter = 1
    while User.objects.filter(username=final_username).exists():
        final_username = f"{base_username}_{counter}"
        counter += 1

    with transaction.atomic():
        user = User.objects.create(
            telegram_id=telegram_id,
            username=final_username,
            full_name=full_name or "",
        )
    logger.info(f"New user registered: telegram_id={telegram_id}, username={final_username}")
    return user, True


async def aget_user_by_telegram_id(telegram_id: int) -> User | None:
    return await User.objects.filter(telegram_id=telegram_id, is_active=True).select_related("department").afirst()


def get_all_active_employees():
    return User.objects.filter(role=UserRole.EMPLOYEE, is_active=True).select_related("department").order_by("full_name")


async def aget_all_active_bosses():
    return User.objects.filter(role=UserRole.BOSS, is_active=True)


def get_department_employees(department_id: int):
    return User.objects.filter(
        department_id=department_id,
        role=UserRole.EMPLOYEE,
        is_active=True,
    ).order_by("full_name")


def get_department_head(department_id: int) -> "User | None":
    return User.objects.filter(
        department_id=department_id,
        role=UserRole.HEAD,
        is_active=True,
    ).first()


async def aget_department_head(department_id: int) -> User | None:
    return await User.objects.filter(
        department_id=department_id,
        role=UserRole.HEAD,
        is_active=True,
    ).afirst()


# ---------------------------------------------------------------------------
# Async wrappers — use these inside AsyncTeleBot handlers (async context).
# All DB work runs in a thread-pool via sync_to_async so Django's ORM is safe.
# ---------------------------------------------------------------------------


@sync_to_async
def aget_all_active_employees() -> list:
    return list(get_all_active_employees())


@sync_to_async
def aget_department_employees(department_id: int) -> list:
    return list(get_department_employees(department_id))

