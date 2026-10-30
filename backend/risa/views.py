import mimetypes
import os
import re

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponsePermanentRedirect,
    StreamingHttpResponse,
)
from django.views.decorators.http import require_http_methods

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")


def _ranged(path: str, start: int, end: int, chunk: int = 256 * 1024):
    with open(path, "rb") as f:
        f.seek(start)
        left = end - start + 1
        while left > 0:
            data = f.read(min(chunk, left))
            if not data:
                break
            left -= len(data)
            yield data


@require_http_methods(["GET", "HEAD"])
def media(request, key: str):
    """Filesystem storage only, with HTTP range requests so COGs can be read in place.
    In production on a box, nginx can serve MEDIA_ROOT directly instead."""
    if settings.STORAGE != "filesystem" or ".." in key.split("/") or key.startswith("uploads/"):
        raise Http404
    path = default_storage.path(key)
    if not os.path.isfile(path):
        raise Http404
    size = os.path.getsize(path)
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    if key.endswith((".tif", ".tiff")):
        ctype = "image/tiff"
    m = RANGE_RE.match(request.headers.get("Range", ""))
    if m and (m.group(1) or m.group(2)):
        if m.group(1):
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else size - 1
        else:
            start, end = max(0, size - int(m.group(2))), size - 1
        end = min(end, size - 1)
        if start > end:
            r = HttpResponse(status=416)
            r["Content-Range"] = f"bytes */{size}"
            return r
        r = StreamingHttpResponse(_ranged(path, start, end), status=206, content_type=ctype)
        r["Content-Range"] = f"bytes {start}-{end}/{size}"
        r["Content-Length"] = str(end - start + 1)
    else:
        r = FileResponse(open(path, "rb"), content_type=ctype)
        r["Content-Length"] = str(size)
    r["Accept-Ranges"] = "bytes"
    r["Access-Control-Allow-Origin"] = "*"
    r["Access-Control-Expose-Headers"] = "Content-Range, Content-Length, Accept-Ranges"
    r["Cache-Control"] = "public, max-age=3600"
    return r


def spa(request):
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        return HttpResponse(
            "Frontend not built. In development run `npm run dev` in frontend/ and open http://localhost:5173",
            content_type="text/plain",
            status=404,
        )
    r = HttpResponse(index.read_bytes(), content_type="text/html")
    r["X-Robots-Tag"] = "noindex"
    r["Cache-Control"] = "no-cache"
    return r


def guide(request):
    """The user guide, a static page in the built frontend (frontend/public/guide/). Its
    assets are relative, so it needs the trailing slash; WhiteNoise serves them."""
    if not request.path.endswith("/"):
        return HttpResponsePermanentRedirect(request.path + "/")
    index = settings.FRONTEND_DIST / "guide" / "index.html"
    if not index.exists():
        return HttpResponse("Frontend not built.", content_type="text/plain", status=404)
    r = HttpResponse(index.read_bytes(), content_type="text/html")
    r["Cache-Control"] = "no-cache"
    return r

