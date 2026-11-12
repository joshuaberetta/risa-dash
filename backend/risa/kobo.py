"""
KoboToolbox: server allow-list, token encryption, form inspection, and sync of
submissions into features.

Servers: ALLOWED_SERVERS lists the servers this instance may use (kf and eu by
default). An http:// server is accepted only when listed exactly, and the token is
only ever sent to the server it was saved for.
"""

import base64
import hashlib
import io
import json
import logging
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.gis.geos import LineString, Point, Polygon
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from .models import Feature, KoboSource
from .symbology import match_status, match_type, symbology

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


# The RISA template's questions (templates/xlsform/, the data contract in
# plans/xlsform-template-and-sop.md). Choice names are RISA codes, so no guessing.
RISA_FORM_ID = "risa_obs"
RISA_PATHS = {"geo": "obs/location", "type": "obs/feature_type", "status": "obs/status", "label": "obs/feature_id",
              "note": "note", "count": "obs/count"}
# Who collected it, and where the form was opened: not needed on the map
RISA_SENSITIVE = ["username", "deviceid", "start_geopoint"]


def form_id(asset: dict) -> str:
    """The form's id_string (form_id in the XLSForm). Kobo keeps settings as a dict, older
    assets as a one-row list."""
    st = (asset.get("content") or {}).get("settings") or {}
    if isinstance(st, list):
        st = st[0] if st else {}
    return str(st.get("id_string") or st.get("form_id") or "")


def is_risa_form(asset: dict, questions: list[dict] | None = None) -> bool:
    """The RISA template, or a country's copy of it (risa_obs_<iso3>, or renamed but with
    the template's type and status questions)."""
    if form_id(asset).startswith(RISA_FORM_ID):
        return True
    paths = {q["path"] for q in (questions if questions is not None else form_questions(asset))}
    return {RISA_PATHS["type"], RISA_PATHS["status"]} <= paths


def _choice_labels(questions: list[dict]) -> dict:
    return {q["path"]: {c["name"]: c["label"] for c in q.get("choices", [])} for q in questions if q.get("choices")}


def risa_field_map(questions: list[dict]) -> dict:
    """The field map of the RISA template, straight from the contract. The type and status
    maps are identity (a country can still edit them in the mapping dialog)."""
    qmap = {q["path"]: q for q in questions}
    types = symbology()["types"]
    statuses = symbology()["status"]
    tq, sq = qmap.get(RISA_PATHS["type"], {}), qmap.get(RISA_PATHS["status"], {})
    return {
        "preset": "risa",
        **RISA_PATHS,
        "popup": [p for p in ("obs/feature_id", "obs/status", "obs/status_reason", "obs/count", "note") if p in qmap],
        "sensitive": list(RISA_SENSITIVE),
        # A choice a country added that isn't a RISA code still gets a best guess
        "type_map": {c["name"]: c["name"] if c["name"] in types else match_type(c["name"]) or match_type(c["label"])
                     for c in tq.get("choices", [])},
        "status_map": {c["name"]: c["name"] if c["name"] in statuses else match_status(c["name"]) or match_status(c["label"])
                       for c in sq.get("choices", [])},
        "choice_labels": _choice_labels(questions),
    }


def is_risa_map(fm: dict) -> bool:
    """Still the RISA mapping: its location, type, status and label questions unchanged."""
    return all(fm.get(k) == RISA_PATHS[k] for k in ("geo", "type", "status", "label"))


def field_map_for(asset: dict) -> dict:
    """The RISA preset for a RISA form, the guess for any other."""
    questions = form_questions(asset)
    return risa_field_map(questions) if is_risa_form(asset, questions) else guess_field_map(questions)


def guess_field_map(questions: list[dict]) -> dict:
    """Pick the geopoint, type, status and label questions, as a starting point for a form
    that isn't the RISA template."""
    fm: dict = {"geo": "", "type": "", "status": "", "label": "", "note": "", "count": "", "popup": [], "sensitive": []}
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
    # The free-text comment and the number of units, by name
    for key, types, words in (("note", ("text",), ("note", "comment", "coment", "observ", "remark")),
                              ("count", ("integer", "decimal"), ("count", "how_many", "cantidad", "number_of", "nombre_de"))):
        hit = next((q for q in questions if q["type"] in types and any(w in q["name"].lower() for w in words)), None)
        if hit and hit["path"] != fm["label"]:
            fm[key] = hit["path"]
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
    fm["choice_labels"] = _choice_labels(questions)
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


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def well_known(props: dict, sub: dict, fm: dict) -> None:
    """The comment and the number of units under fixed names, `note` and `count`, so page 2,
    the summary and the analysis read them whatever the form calls them. Without a mapping,
    a top-level `note` question already is one."""
    note = _val(sub, fm.get("note", "")) if fm.get("note") else None
    if note not in (None, ""):
        props["note"] = str(note)
    count = _int(_val(sub, fm.get("count", ""))) if fm.get("count") else None
    if count is not None:
        props["count"] = count


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
            # select_multiple answers are space-separated names: the raw value stays, the labels are joined
            props[f"{k}:label"] = ", ".join(lab.get(x, x) for x in v.split())
    vs = sub.get("_validation_status") or {}
    props["_validation_status"] = vs.get("label", "") if isinstance(vs, dict) else ""
    props["_photos"] = [
        {"id": a.get("id") or a.get("uid"), "name": a.get("media_file_basename") or a.get("filename", "").split("/")[-1],
         "url": a.get("download_small_url") or a.get("download_url"), "large": a.get("download_large_url") or a.get("download_url"),
         "original": a.get("download_url")}
        for a in sub.get("_attachments", [])
        if str(a.get("mimetype", "")).startswith("image/")
    ]
    well_known(props, sub, fm)
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



# ---- photos, with faces hidden (risa/redact.py) ---------------------------------------


def photo_key(layer_id, photo_id, size: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", str(photo_id))
    return f"photos/{layer_id}/{safe}{'_thumb' if size == 'thumb' else ''}.jpg"


def redact_photo(source: KoboSource, ph: dict) -> int:
    """One photo from Kobo, kept with its faces hidden, large and as a thumbnail. Returns
    the number of faces."""
    from . import redact, storage

    out = redact.redact(attachment(source, ph.get("original") or ph.get("large") or ph["url"]).content)
    # The thumbnail last: with it there, both are
    for size in ("large", "thumb"):
        storage.save(photo_key(source.layer_id, ph["id"], size), io.BytesIO(out[size]), content_type="image/jpeg")
    return out["faces"]


def _photos(source: KoboSource):
    for props in source.layer.features.values_list("properties", flat=True):
        yield from props.get("_photos") or []


def redact_photos(source: KoboSource) -> int:
    """Every photo not yet kept. A photo that fails stays hidden, and is tried again on the
    next sync or when someone opens it."""
    done = 0
    for ph in _photos(source):
        if default_storage.exists(photo_key(source.layer_id, ph["id"], "thumb")):
            continue
        try:
            redact_photo(source, ph)
            done += 1
        except Exception:
            log.exception("Photo %s of layer %s not redacted", ph.get("id"), source.layer_id)
    return done


def photo(source: KoboSource, photo_id: str, size: str) -> bytes:
    """A photo with its faces hidden; redacted now if the sync hasn't got to it yet."""
    key = photo_key(source.layer_id, photo_id, size)
    if not default_storage.exists(key):
        ph = next((p for p in _photos(source) if str(p.get("id")) == photo_id), None)
        if not ph:
            raise KoboError("No such photo in this layer")
        redact_photo(source, ph)
    with default_storage.open(key, "rb") as f:
        return f.read()
