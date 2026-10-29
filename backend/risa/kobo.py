"""
KoboToolbox: server allow-list, token encryption, form inspection, and sync of
submissions into features.

Servers: ALLOWED_SERVERS lists the servers this instance may use (kf and eu by
default). An http:// server is accepted only when listed exactly, and the token is
only ever sent to the server it was saved for.
"""

import base64
import hashlib
import json
import logging
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.gis.geos import LineString, Point, Polygon
from django.db import transaction
from django.utils import timezone

from .models import Feature, KoboSource
from .symbology import match_status, match_type

log = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(30.0, connect=10.0)
PAGE = 1000


class KoboError(Exception):
    pass


# ---- servers and tokens -------------------------------------------------------------


def normalise_server(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if url and "://" not in url:
        url = f"https://{url}"
    return url


def check_server(url: str) -> str:
    url = normalise_server(url)
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.path not in {"", "/"}:
        raise KoboError("Enter the server's address, e.g. https://kf.kobotoolbox.org")
    allowed = [normalise_server(s) for s in settings.ALLOWED_SERVERS]
    if url not in allowed:
        raise KoboError(f"{url} is not on this instance's list of Kobo servers ({', '.join(allowed)})")
    return url


def _fernet() -> Fernet:
    secret = settings.TOKEN_KEY or settings.SECRET_KEY
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(blob: str) -> str:
    return _fernet().decrypt(blob.encode()).decode()


def client(server: str, token: str) -> httpx.Client:
    return httpx.Client(
        base_url=server,
        headers={"Authorization": f"Token {token}", "Accept": "application/json"},
        timeout=TIMEOUT,
        follow_redirects=False,
    )


def _get(c: httpx.Client, path: str, **params) -> dict:
    try:
        r = c.get(path, params=params)
    except httpx.HTTPError as e:
        raise KoboError(f"Could not reach {c.base_url}: {e}") from e
    if r.status_code in (401, 403):
        raise KoboError("Kobo refused the token. Check it in Account settings > Security.")
    if r.status_code == 404:
        raise KoboError("Kobo couldn't find that project.")
    if r.is_redirect or r.status_code >= 400:
        raise KoboError(f"Kobo answered {r.status_code} for {path}")
    return r.json()


# ---- projects and forms -----------------------------------------------------------


def list_projects(server: str, token: str) -> list[dict]:
    with client(server, token) as c:
        data = _get(c, "/api/v2/assets/", asset_type="survey", limit=300, metadata="on")
    out = []
    for a in data.get("results", []):
        if not a.get("has_deployment"):
            continue
        out.append(
            {
                "uid": a["uid"],
                "name": a.get("name") or a["uid"],
                "submissions": a.get("deployment__submission_count", 0),
                "modified": a.get("date_modified"),
            }
        )
    return out


def get_asset(server: str, token: str, uid: str) -> dict:
    with client(server, token) as c:
        return _get(c, f"/api/v2/assets/{uid}/")


def _label(row: dict) -> str:
    lab = row.get("label")
    if isinstance(lab, list):
        lab = next((x for x in lab if x), "")
    return str(lab or row.get("name") or row.get("$autoname") or "")


def form_questions(asset: dict) -> list[dict]:
    """Questions with their full path (group/name), type, label and choices."""
    content = asset.get("content") or {}
    choices: dict[str, list[dict]] = {}
    for ch in content.get("choices", []):
        choices.setdefault(ch.get("list_name"), []).append({"name": str(ch.get("name")), "label": _label(ch)})
    out, stack = [], []
    for row in content.get("survey", []):
        t = row.get("type", "")
        name = row.get("name") or row.get("$autoname") or ""
        if t in ("begin_group", "begin_repeat"):
            stack.append(name)
            continue
        if t in ("end_group", "end_repeat"):
            if stack:
                stack.pop()
            continue
        if not name or t in ("note", "start", "end", "today", "deviceid", "calculate"):
            continue
        base = t.split(" ")[0]
        q = {"path": "/".join([*stack, name]), "name": name, "type": base, "label": _label(row)}
        if base in ("select_one", "select_multiple"):
            q["choices"] = choices.get(row.get("select_from_list_name"), [])
        out.append(q)
    return out


def guess_field_map(questions: list[dict]) -> dict:
    """Pick the geopoint, type, status and label questions. Works for the RISA form
    without setup, and as a starting point for other forms."""
    fm: dict = {"geo": "", "type": "", "status": "", "label": "", "popup": [], "sensitive": []}
    geo = [q for q in questions if q["type"] in ("geopoint", "geoshape", "geotrace")]
    if geo:
        fm["geo"] = geo[0]["path"]

    def score(q, matcher, words):
        s = 0
        if any(w in q["name"].lower() for w in words):
            s += 2
        hits = sum(1 for c in q.get("choices", []) if matcher(c["name"]) or matcher(c["label"]))
        if hits >= 2:
            s += hits
        return s

    selects = [q for q in questions if q["type"] == "select_one"]
    for key, matcher, words in (
        ("status", match_status, ("status", "estado", "statut", "condition", "funcion")),
        ("type", match_type, ("type", "tipo", "categor", "service", "servicio", "infra")),
    ):
        ranked = sorted(((score(q, matcher, words), q) for q in selects), key=lambda x: -x[0])
        ranked = [(s, q) for s, q in ranked if s > 0 and q["path"] not in (fm["status"], fm["type"])]
        if ranked:
            fm[key] = ranked[0][1]["path"]
    texts = [q for q in questions if q["type"] == "text"]
    named = [q for q in texts if any(w in q["name"].lower() for w in ("name", "nombre", "nom", "label", "id"))]
    if named or texts:
        fm["label"] = (named or texts)[0]["path"]
    fm["popup"] = [q["path"] for q in questions if q["type"] not in ("geopoint", "geoshape", "geotrace")][:12]
    fm["sensitive"] = [
        q["path"] for q in questions if any(w in q["name"].lower() for w in ("phone", "telefono", "name_of", "contact"))
    ]
    # Maps from choice names to RISA values, editable in the UI
    qmap = {q["path"]: q for q in questions}
    for key, matcher in (("status", match_status), ("type", match_type)):
        q = qmap.get(fm[key])
        if q:
            fm[f"{key}_map"] = {c["name"]: (matcher(c["name"]) or matcher(c["label"]) or "") for c in q["choices"]}
    fm["choice_labels"] = {
        q["path"]: {c["name"]: c["label"] for c in q.get("choices", [])} for q in questions if q.get("choices")
    }
    return fm


# ---- submissions -> features ------------------------------------------------------


def _val(sub: dict, path: str):
    if not path:
        return None
    if path in sub:
        return sub[path]
    # Kobo keys can include or omit group prefixes depending on export settings
    leaf = path.split("/")[-1]
    for k, v in sub.items():
        if k == leaf or k.endswith(f"/{leaf}"):
            return v
    return None


def _coords(text: str) -> list[tuple[float, float]]:
    pts = []
    for chunk in str(text).split(";"):
        bits = chunk.strip().split()
        if len(bits) >= 2:
            pts.append((float(bits[1]), float(bits[0])))  # Kobo: lat lon alt acc
    return pts


def geometry(sub: dict, fm: dict):
    raw = _val(sub, fm.get("geo", ""))
    try:
        if raw:
            pts = _coords(raw)
            if len(pts) == 1:
                return Point(*pts[0], srid=4326)
            if len(pts) >= 4 and pts[0] == pts[-1]:
                return Polygon(pts, srid=4326)
            if len(pts) >= 2:
                return LineString(pts, srid=4326)
    except (ValueError, TypeError):
        pass
    gl = sub.get("_geolocation") or []
    if len(gl) == 2 and gl[0] is not None and gl[1] is not None:
        return Point(float(gl[1]), float(gl[0]), srid=4326)
    return None


def to_feature_fields(sub: dict, fm: dict) -> dict:
    sensitive = set(fm.get("sensitive", []))
    labels = fm.get("choice_labels", {})
    props = {}
    for k, v in sub.items():
        if k.startswith("_") and k not in ("_id", "_uuid", "_submission_time", "_validation_status"):
            continue
        if k in sensitive or any(k.endswith(f"/{s.split('/')[-1]}") for s in sensitive):
            continue
        if k in ("meta/instanceID", "formhub/uuid", "__version__", "meta/rootUuid", "meta/deprecatedID"):
            continue
        props[k] = v
        lab = labels.get(k) or next((labels[p] for p in labels if p.split("/")[-1] == k.split("/")[-1]), None)
        if lab and isinstance(v, str):
            props[f"{k}:label"] = " ".join(lab.get(x, x) for x in v.split())
    vs = sub.get("_validation_status") or {}
    props["_validation_status"] = vs.get("label", "") if isinstance(vs, dict) else ""
    props["_photos"] = [
        {"id": a.get("id") or a.get("uid"), "name": a.get("media_file_basename") or a.get("filename", "").split("/")[-1],
         "url": a.get("download_small_url") or a.get("download_url"), "large": a.get("download_large_url") or a.get("download_url")}
        for a in sub.get("_attachments", [])
        if str(a.get("mimetype", "")).startswith("image/")
    ]
    tval = _val(sub, fm.get("type", ""))
    sval = _val(sub, fm.get("status", ""))
    rtype = fm.get("type_map", {}).get(str(tval), "") if tval is not None else ""
    rstatus = fm.get("status_map", {}).get(str(sval), "") if sval is not None else ""
    rtype = rtype or match_type(tval)
    rstatus = rstatus or match_status(sval)
    label = _val(sub, fm.get("label", "")) or ""
    observed = None
    ts = sub.get("end") or sub.get("_submission_time")
    if ts:
        try:
            observed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if timezone.is_naive(observed):
                observed = timezone.make_aware(observed, UTC)
        except ValueError:
            observed = None
    return {"properties": props, "risa_type": rtype, "risa_status": rstatus or "unknown",
            "label": str(label)[:200], "observed_at": observed}


def sync(source: KoboSource, full: bool = False) -> int:
    """Pull new submissions (or all, with full=True). Returns the number written."""
    token = decrypt_token(source.token_encrypted)
    fm = source.field_map or {}
    written, start = 0, 0
    last_id = 0 if full else source.last_submission_id
    max_id = last_id
    with client(source.server_url, token) as c:
        while True:
            params = {"format": "json", "limit": PAGE, "start": start, "sort": '{"_id": 1}'}
            if last_id:
                params["query"] = json.dumps({"_id": {"$gt": last_id}})
            data = _get(c, f"/api/v2/assets/{source.asset_uid}/data/", **params)
            subs = data.get("results", [])
            with transaction.atomic():
                for sub in subs:
                    geom = geometry(sub, fm)
                    max_id = max(max_id, int(sub.get("_id") or 0))
                    if geom is None:
                        continue
                    fields = to_feature_fields(sub, fm)
                    Feature.objects.update_or_create(
                        layer=source.layer, source_ref=str(sub.get("_uuid") or sub.get("_id")),
                        defaults={"geom": geom, **fields},
                    )
                    written += 1
            if not data.get("next") or not subs:
                break
            start += len(subs)
    source.last_submission_id = max_id
    source.last_synced_at = timezone.now()
    source.last_error = ""
    source.submission_count = source.layer.features.count()
    source.save()
    _update_bbox(source.layer)
    return written


def _update_bbox(layer) -> None:
    from django.contrib.gis.db.models import Extent

    ext = layer.features.aggregate(e=Extent("geom"))["e"]
    if ext:
        layer.bbox = list(ext)
        layer.save(update_fields=["bbox", "updated_at"])


def attachment(source: KoboSource, url: str) -> httpx.Response:
    """Fetch a photo for the popup. Only from the source's own server."""
    if urlsplit(url).netloc != urlsplit(source.server_url).netloc:
        raise KoboError("Attachment is not on this project's server")
    token = decrypt_token(source.token_encrypted)
    with httpx.Client(headers={"Authorization": f"Token {token}"}, timeout=TIMEOUT, follow_redirects=True) as c:
        r = c.get(url)
    # Kobo may redirect to its file storage; httpx drops the token on a cross-origin redirect
    if r.status_code >= 400:
        raise KoboError(f"Kobo answered {r.status_code} for the photo")
    return r

