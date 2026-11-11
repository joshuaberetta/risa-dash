import pytest


@pytest.fixture
def media(settings, tmp_path):
    """Stored files in a temporary folder. STORAGES too: its location is set explicitly, so
    MEDIA_ROOT alone doesn't move it."""
    root = tmp_path / "media"
    settings.STORAGE = "filesystem"
    settings.MEDIA_ROOT = str(root)
    settings.STORAGES = {**settings.STORAGES, "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": str(root), "base_url": "/media/"}}}
    return tmp_path
