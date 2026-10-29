"""File storage helpers that work the same on S3 (Spaces) and the local filesystem."""

import os
import shutil
import tempfile
from contextlib import contextmanager

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage


def is_s3() -> bool:
    return settings.STORAGE == "s3"


def save(key: str, path_or_file, public: bool = False, content_type: str | None = None) -> str:
    """Write a local file (path) or file object to `key`. Returns the key."""
    if is_s3():
        client = default_storage.connection.meta.client
        extra = {}
        if public:
            extra["ACL"] = "public-read"
        if content_type:
            extra["ContentType"] = content_type
        full = default_storage._normalize_name(key)
        if isinstance(path_or_file, str | os.PathLike):
            client.upload_file(str(path_or_file), default_storage.bucket_name, full, ExtraArgs=extra)
        else:
            client.upload_fileobj(path_or_file, default_storage.bucket_name, full, ExtraArgs=extra)
        return key
    if default_storage.exists(key):
        default_storage.delete(key)
    if isinstance(path_or_file, str | os.PathLike):
        with open(path_or_file, "rb") as f:
            default_storage.save(key, File(f))
    else:
        default_storage.save(key, File(path_or_file))
    return key


def url(key: str, public: bool = False) -> str:
    """A URL the browser (and QGIS) can range-read."""
    if not key:
        return ""
    if is_s3():
        if public and settings.MEDIA_PUBLIC_URL:
            prefix = f"{settings.STORAGES['default']['OPTIONS']['location']}/".lstrip("/")
            return f"{settings.MEDIA_PUBLIC_URL}/{prefix}{key}"
        return default_storage.url(key)
    return f"{settings.MEDIA_URL}{key}"


def absolute_url(key: str, public: bool = False) -> str:
    u = url(key, public)
    return u if u.startswith("http") else f"{settings.PUBLIC_URL}{u}"


@contextmanager
def local_copy(key: str, suffix: str = ""):
    """Yields a local path for a stored file (downloads it on S3)."""
    if not is_s3():
        yield default_storage.path(key)
        return
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        client = default_storage.connection.meta.client
        client.download_file(default_storage.bucket_name, default_storage._normalize_name(key), path)
        yield path
    finally:
        os.unlink(path)


def concat_parts(keys: list[str], dest_path: str) -> None:
    with open(dest_path, "wb") as out:
        for k in keys:
            with default_storage.open(k, "rb") as f:
                shutil.copyfileobj(f, out, 1024 * 1024)


def delete_prefix(prefix: str) -> None:
    try:
        dirs, files = default_storage.listdir(prefix)
    except FileNotFoundError:
        return
    for f in files:
        default_storage.delete(f"{prefix.rstrip('/')}/{f}")
    for d in dirs:
        delete_prefix(f"{prefix.rstrip('/')}/{d}")
