"""No accounts: editing a response needs its edit key, sent as the X-Edit-Key header."""

from django.conf import settings
from ninja.errors import HttpError

from .models import Response


def edit_key(request) -> str:
    return request.headers.get("X-Edit-Key", "")


def can_edit(request, response: Response) -> bool:
    return response.check_edit_key(edit_key(request))


def require_edit(request, response: Response) -> None:
    if not can_edit(request, response):
        raise HttpError(403, "This needs the response's edit key")


def require_view(request, response: Response) -> None:
    if not settings.READ_ONLY_PUBLIC and not can_edit(request, response):
        raise HttpError(403, "This instance needs the response's edit key to view")


def require_create(request) -> None:
    if settings.CREATE_KEY and request.headers.get("X-Create-Key", "") != settings.CREATE_KEY:
        raise HttpError(403, "Creating a response needs this instance's create key")
