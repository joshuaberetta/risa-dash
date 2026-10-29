import json
import os
import tempfile
from datetime import date

from django.conf import settings
from django.contrib.gis.db.models import Extent
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, Max, Min
from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError

from . import exports, kobo, storage
from .access import can_edit, require_create, require_edit, require_view
from .ingest import IngestError, kind_for
from .models import Feature, KoboSource, Layer, Product, ProductVersion, Response, Site, Upload
from .summary import site_summary
from .symbology import symbology

api = NinjaAPI(title="RISA Dashboard API", version="0.1", urls_namespace="api")


@api.exception_handler(kobo.KoboError)
def kobo_error(request, exc):
    return api.create_response(request, {"detail": str(exc)}, status=400)


@api.exception_handler(IngestError)
def ingest_error(request, exc):
    return api.create_response(request, {"detail": str(exc)}, status=400)


# ---- serialisers --------------------------------------------------------------------


def response_dict(r: Response, request=None) -> dict:
    return {
        "id": r.id, "slug": r.slug, "name": r.name, "hazard": r.hazard, "country": r.country, "glide": r.glide,
        "start_date": r.start_date, "language": r.language, "private": r.private,
        "can_edit": can_edit(request, r) if request else False,
    }


def site_dict(s: Site) -> dict:
    return {
        "id": s.id, "slug": s.slug, "name": s.name, "place": s.place, "kind": s.kind,
        "default_view": s.default_view, "notes": s.notes,
    }


def layer_dict(lyr: Layer) -> dict:
    d = {
        "id": lyr.id, "name": lyr.name, "kind": lyr.kind, "status": lyr.status, "error": lyr.error,
        "style": lyr.style, "z_order": lyr.z_order, "visible_default": lyr.visible_default,
        "attribution": lyr.attribution, "licence": lyr.licence, "captured_at": lyr.captured_at,
        "resolution_cm": lyr.resolution_cm, "bbox": lyr.bbox, "online_only": lyr.online_only,
        "updated_at": lyr.updated_at,
    }
    if lyr.kind == "raster" and lyr.status == "ready":
        d["url"] = storage.url(lyr.source, public=True)
    elif lyr.kind in ("xyz", "wms", "cog_url"):
        d["url"] = lyr.source
    elif lyr.is_vector:
        d["url"] = f"/api/layers/{lyr.id}/features?t={int(lyr.updated_at.timestamp())}"
        d["feature_count"] = getattr(lyr, "n_features", None)
    if lyr.kind == "kobo" and hasattr(lyr, "kobo"):
        k = lyr.kobo
        d["kobo"] = {"server": k.server_url, "asset_uid": k.asset_uid, "asset_name": k.asset_name,
                     "last_synced_at": k.last_synced_at, "last_error": k.last_error,
                     "submissions": k.submission_count, "auto_sync": k.auto_sync}
    if lyr.original:
        d["download"] = f"/api/layers/{lyr.id}/original"
    return d


def product_dict(p: Product) -> dict:
    return {
        "id": p.id, "site": p.site_id, "kind": p.kind, "title": p.title, "code": p.code,
        "version_label": p.version_label, "page_size": p.page_size, "view": p.view,
        "key_message": p.key_message, "glance": p.glance, "authority": p.authority, "sources": p.sources,
        "disclaimer": p.disclaimer, "credits": p.credits, "updated_at": p.updated_at,
        "versions": [version_dict(v) for v in p.versions.all()[:20]],
        "preview": {
            "status": p.preview_status, "error": p.preview_error, "at": p.preview_at,
            "url": f"/api/products/{p.id}/preview.png?t={int(p.preview_at.timestamp())}" if p.preview_key and p.preview_at else None,
        },
    }


def version_dict(v: ProductVersion) -> dict:
    return {
        "n": v.n, "status": v.status, "error": v.error, "rendered_at": v.rendered_at,
        "pdf": f"/api/products/{v.product_id}/versions/{v.n}/pdf" if v.pdf_key else None,
    }


def basemaps() -> list[dict]:
    """Local PMTiles extracts first (work offline), then online ones when enabled."""
    out = []
    try:
        _, files = default_storage.listdir("basemaps")
    except (FileNotFoundError, NotImplementedError):
        files = []
    for f in sorted(files):
        if f.endswith(".pmtiles"):
            out.append({"id": f"pmtiles:{f}", "name": f"Offline: {f[:-8]}", "kind": "pmtiles",
                        "url": storage.absolute_url(f"basemaps/{f}", public=True), "online": False,
                        "attribution": "© OpenStreetMap contributors, Protomaps"})
    if settings.ONLINE_BASEMAPS:
        out += [
            {"id": "positron", "name": "Light (OpenFreeMap)", "kind": "style", "online": True,
             "url": "https://tiles.openfreemap.org/styles/positron",
             "attribution": "OpenFreeMap © OpenMapTiles, © OpenStreetMap contributors"},
            {"id": "liberty", "name": "Streets (OpenFreeMap)", "kind": "style", "online": True,
             "url": "https://tiles.openfreemap.org/styles/liberty",
             "attribution": "OpenFreeMap © OpenMapTiles, © OpenStreetMap contributors"},
            {"id": "esri-imagery", "name": "Satellite (Esri World Imagery)", "kind": "raster", "online": True,
             "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
             "maxzoom": 19, "attribution": "Esri, Maxar, Earthstar Geographics, and the GIS User Community"},
            {"id": "osm", "name": "OpenStreetMap", "kind": "raster", "online": True,
             "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png", "maxzoom": 19,
             "attribution": "© OpenStreetMap contributors"},
        ]
    out.append({"id": "none", "name": "No basemap", "kind": "none", "online": False, "attribution": ""})
    return out


@api.get("/config")
def config(request):
    return {
        "symbology": symbology(),
        "basemaps": basemaps(),
        "glyphs": settings.GLYPHS_URL,
        "allowed_servers": settings.ALLOWED_SERVERS,
        "create_key_required": bool(settings.CREATE_KEY),
        "read_only_public": settings.READ_ONLY_PUBLIC,
        "chunk_size": settings.UPLOAD_CHUNK_SIZE,
    }


# ---- responses ------------------------------------------------------------------------


class ResponseIn(Schema):
    name: str
    slug: str = ""
    hazard: str = ""
    country: str = ""
    glide: str = ""
    start_date: date | None = None
    language: str = "en"
    private: bool = False


class ResponsePatch(Schema):
    name: str | None = None
    hazard: str | None = None
    country: str | None = None
    glide: str | None = None
    start_date: date | None = None
    language: str | None = None
    private: bool | None = None


def unique_slug(base: str, qs, field="slug") -> str:
    base = slugify(base)[:70] or "item"
    slug, i = base, 2
    while qs.filter(**{field: slug}).exists():
        slug, i = f"{base}-{i}", i + 1
    return slug


@api.get("/responses")
def list_responses(request):
    qs = Response.objects.filter(private=False) if settings.READ_ONLY_PUBLIC else Response.objects.none()
    return [{**response_dict(r), "sites": r.sites.count()} for r in qs]


@api.post("/responses")
def create_response(request, data: ResponseIn):
    require_create(request)
    r = Response(**data.dict(exclude={"slug"}))
    r.slug = unique_slug(data.slug or data.name, Response.objects)
    key = r.set_edit_key()
    r.save()
    return {"response": response_dict(r), "edit_key": key}


@api.get("/responses/{slug}")
def get_response(request, slug: str):
    r = get_object_or_404(Response, slug=slug)
    require_view(request, r)
    return {**response_dict(r, request), "sites": [site_dict(s) for s in r.sites.all()]}


@api.patch("/responses/{slug}")
def patch_response(request, slug: str, data: ResponsePatch):
    r = get_object_or_404(Response, slug=slug)
    require_edit(request, r)
    for k, v in data.dict(exclude_unset=True).items():
        setattr(r, k, v)
    r.save()
    return response_dict(r, request)


@api.post("/responses/{slug}/check-key")
def check_key(request, slug: str):
    r = get_object_or_404(Response, slug=slug)
    return {"ok": can_edit(request, r)}


# ---- sites -------------------------------------------------------------------------


class SiteIn(Schema):
    name: str
    place: str = ""
    kind: str = "camp"
    center: list[float] | None = None
    zoom: float | None = None


class SitePatch(Schema):
    name: str | None = None
    place: str | None = None
    kind: str | None = None
    notes: str | None = None
    default_view: dict | None = None


@api.post("/responses/{slug}/sites")
def create_site(request, slug: str, data: SiteIn):
    r = get_object_or_404(Response, slug=slug)
    require_edit(request, r)
    view = {"center": data.center, "zoom": data.zoom or 16} if data.center else {}
    s = Site.objects.create(response=r, name=data.name, place=data.place, kind=data.kind, default_view=view,
                            slug=unique_slug(data.name, r.sites))
    return site_dict(s)


def _site_full(request, s: Site) -> dict:
    # Meta.ordering is ignored on aggregated queries
    layers = s.layers.select_related("kobo").annotate(n_features=Count("features")).order_by("-z_order", "created_at")
    return {
        **site_dict(s),
        "response": response_dict(s.response, request),
        "layers": [layer_dict(lyr) for lyr in layers],
        "products": [product_dict(p) for p in s.products.prefetch_related("versions")],
    }


@api.get("/responses/{rslug}/sites/{sslug}")
def get_site(request, rslug: str, sslug: str):
    s = get_object_or_404(Site.objects.select_related("response"), response__slug=rslug, slug=sslug)
    require_view(request, s.response)
    return _site_full(request, s)


def _site(request, site_id, edit=True) -> Site:
    s = get_object_or_404(Site.objects.select_related("response"), id=site_id)
    (require_edit if edit else require_view)(request, s.response)
    return s


@api.get("/sites/{site_id}")
def get_site_by_id(request, site_id: str):
    return _site_full(request, _site(request, site_id, edit=False))


@api.patch("/sites/{site_id}")
def patch_site(request, site_id: str, data: SitePatch):
    s = _site(request, site_id)
    for k, v in data.dict(exclude_unset=True).items():
        setattr(s, k, v)
    s.save()
    return site_dict(s)


@api.get("/sites/{site_id}/summary")
def get_summary(request, site_id: str, layers: str = ""):
    s = _site(request, site_id, edit=False)
    ids = [x for x in layers.split(",") if x] or None
    return site_summary(s, ids)


@api.get("/sites/{site_id}/export.gpkg")
def export_gpkg(request, site_id: str):
    s = _site(request, site_id, edit=False)
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, f"{s.response.slug}_{s.slug}.gpkg")
    exports.site_geopackage(s, path)
    if not os.path.exists(path):
        raise HttpError(404, "This site has no vector data to export yet")
    return FileResponse(open(path, "rb"), as_attachment=True, filename=os.path.basename(path),
                        content_type="application/geopackage+sqlite3")


# ---- layers ------------------------------------------------------------------------


class UrlLayerIn(Schema):
    name: str
    kind: str  # xyz | wms | cog_url
    source: str
    attribution: str = ""
    captured_at: date | None = None


class LayerPatch(Schema):
    name: str | None = None
    style: dict | None = None
    visible_default: bool | None = None
    attribution: str | None = None
    licence: str | None = None
    captured_at: date | None = None
    resolution_cm: float | None = None


def _layer(request, layer_id, edit=True) -> Layer:
    lyr = get_object_or_404(Layer.objects.select_related("site__response"), id=layer_id)
    (require_edit if edit else require_view)(request, lyr.site.response)
    return lyr


def _next_z(site: Site, kind: str = "vector") -> int:
    """New vector layers go on top; new imagery goes under everything, where it's most useful."""
    if kind in ("raster", "xyz", "wms", "cog_url"):
        return (site.layers.aggregate(m=Min("z_order"))["m"] or 0) - 1
    return (site.layers.aggregate(m=Max("z_order"))["m"] or 0) + 1


@api.post("/sites/{site_id}/layers")
def create_url_layer(request, site_id: str, data: UrlLayerIn):
    s = _site(request, site_id)
    if data.kind not in ("xyz", "wms", "cog_url"):
        raise HttpError(400, "kind must be xyz, wms or cog_url")
    if not data.source.startswith(("http://", "https://")):
        raise HttpError(400, "Enter a full URL")
    lyr = Layer.objects.create(site=s, name=data.name, kind=data.kind, source=data.source, online_only=True,
                               attribution=data.attribution, captured_at=data.captured_at, z_order=_next_z(s, data.kind))
    return layer_dict(lyr)


@api.get("/layers/{layer_id}/features")
def layer_features(request, layer_id: str, t: str = ""):
    lyr = _layer(request, layer_id, edit=False)
    r = HttpResponse(content_type="application/geo+json")
    r.write(json.dumps(exports.layer_geojson(lyr), default=str, ensure_ascii=False))
    r["Cache-Control"] = "public, max-age=31536000" if t else "no-cache"
    return r


@api.get("/layers/{layer_id}/original")
def layer_original(request, layer_id: str):
    lyr = _layer(request, layer_id, edit=False)
    if not lyr.original:
        raise HttpError(404, "No original file")
    if storage.is_s3():
        return HttpResponseRedirect(storage.url(lyr.original))
    return FileResponse(default_storage.open(lyr.original, "rb"), as_attachment=True,
                        filename=f"{slugify(lyr.name)}{os.path.splitext(lyr.original)[1]}")


@api.patch("/layers/{layer_id}")
def patch_layer(request, layer_id: str, data: LayerPatch):
    lyr = _layer(request, layer_id)
    for k, v in data.dict(exclude_unset=True).items():
        setattr(lyr, k, v)
    lyr.save()
    return layer_dict(lyr)


@api.delete("/layers/{layer_id}")
def delete_layer(request, layer_id: str):
    lyr = _layer(request, layer_id)
    storage.delete_prefix(f"layers/{lyr.id}")
    lyr.delete()
    return {"ok": True}


class ReorderIn(Schema):
    ids: list[str]  # top first


@api.post("/sites/{site_id}/layers/reorder")
def reorder_layers(request, site_id: str, data: ReorderIn):
    s = _site(request, site_id)
    n = len(data.ids)
    with transaction.atomic():
        for i, lid in enumerate(data.ids):
            s.layers.filter(id=lid).update(z_order=n - i)
    return {"ok": True}


# ---- features (drawing and editing) ------------------------------------------------


class FeatureIn(Schema):
    geometry: dict
    risa_type: str = ""
    risa_status: str = ""
    label: str = ""
    properties: dict = {}


class FeaturePatch(Schema):
    geometry: dict | None = None
    risa_type: str | None = None
    risa_status: str | None = None
    label: str | None = None
    properties: dict | None = None


def _geom(gj: dict):
    try:
        g = GEOSGeometry(json.dumps(gj), srid=4326)
    except (GEOSException, ValueError, TypeError) as e:
        raise HttpError(400, f"Invalid geometry: {e}") from e
    return g


def _check_status(st: str | None):
    if st and st not in ("ok", "partial", "no", "unknown"):
        raise HttpError(400, "risa_status must be ok, partial, no or unknown")


def feature_dict(f: Feature) -> dict:
    return {"type": "Feature", "id": str(f.id), "geometry": json.loads(f.geom.geojson),
            "properties": {**f.properties, "risa_id": str(f.id), "risa_type": f.risa_type,
                           "risa_status": f.risa_status, "risa_label": f.label}}


@api.post("/sites/{site_id}/annotations")
def add_annotation(request, site_id: str, data: FeatureIn):
    """Drawn features go to the site's Annotations layer, made on first use."""
    s = _site(request, site_id)
    _check_status(data.risa_status)
    lyr = s.layers.filter(kind="annotations").first() or Layer.objects.create(
        site=s, name="Annotations", kind="annotations", z_order=_next_z(s), style={"preset": "risa"})
    f = Feature.objects.create(layer=lyr, geom=_geom(data.geometry), risa_type=data.risa_type,
                               risa_status=data.risa_status or "", label=data.label, properties=data.properties)
    lyr.save(update_fields=["updated_at"])
    _bbox(lyr)
    return {"layer": layer_dict(lyr), "feature": feature_dict(f)}


def _bbox(lyr: Layer):
    e = lyr.features.aggregate(e=Extent("geom"))["e"]
    lyr.bbox = list(e) if e else None
    lyr.save(update_fields=["bbox", "updated_at"])


def _feature(request, fid) -> Feature:
    f = get_object_or_404(Feature.objects.select_related("layer__site__response"), id=fid)
    require_edit(request, f.layer.site.response)
    return f


@api.patch("/features/{fid}")
def patch_feature(request, fid: str, data: FeaturePatch):
    f = _feature(request, fid)
    d = data.dict(exclude_unset=True)
    _check_status(d.get("risa_status"))
    if "geometry" in d:
        f.geom = _geom(d.pop("geometry"))
    if "label" in d:
        f.label = d.pop("label")
    for k, v in d.items():
        setattr(f, k, v)
    f.save()
    _bbox(f.layer)
    return feature_dict(f)


@api.delete("/features/{fid}")
def delete_feature(request, fid: str):
    f = _feature(request, fid)
    lyr = f.layer
    f.delete()
    _bbox(lyr)
    return {"ok": True}


# ---- uploads (chunked, resumable) --------------------------------------------------


class UploadIn(Schema):
    filename: str
    size: int
    name: str = ""
    captured_at: date | None = None
    attribution: str = ""


@api.post("/sites/{site_id}/uploads")
def start_upload(request, site_id: str, data: UploadIn):
    s = _site(request, site_id)
    if data.size <= 0 or data.size > settings.MAX_UPLOAD_SIZE:
        raise HttpError(400, f"Files up to {settings.MAX_UPLOAD_SIZE // 1024**3} GB")
    kind = kind_for(data.filename)
    u = Upload.objects.create(
        site=s, filename=os.path.basename(data.filename)[:300], size=data.size, kind=kind,
        chunk_size=settings.UPLOAD_CHUNK_SIZE, layer_name=data.name or os.path.splitext(data.filename)[0],
        layer_options={"captured_at": data.captured_at.isoformat() if data.captured_at else None,
                       "attribution": data.attribution},
    )
    return {"id": u.id, "chunk_size": u.chunk_size, "parts": u.part_count, "kind": kind}


def _upload(request, upload_id) -> Upload:
    u = get_object_or_404(Upload.objects.select_related("site__response"), id=upload_id)
    require_edit(request, u.site.response)
    return u


@api.get("/uploads/{upload_id}")
def upload_status(request, upload_id: str):
    u = _upload(request, upload_id)
    try:
        _, files = default_storage.listdir(f"uploads/{u.id}")
    except FileNotFoundError:
        files = []
    return {"id": u.id, "parts": u.part_count, "received": sorted(int(f) for f in files if f.isdigit()),
            "completed": u.completed}


@api.put("/uploads/{upload_id}/parts/{n}")
def upload_part(request, upload_id: str, n: int):
    u = _upload(request, upload_id)
    if u.completed or not 0 <= n < u.part_count:
        raise HttpError(400, "Bad part number")
    body = request.body
    expected = u.chunk_size if n < u.part_count - 1 else u.size - u.chunk_size * (u.part_count - 1)
    if len(body) != expected:
        raise HttpError(400, f"Part {n} should be {expected} bytes, got {len(body)}")
    key = u.part_key(n)
    if default_storage.exists(key):
        default_storage.delete(key)
    default_storage.save(key, ContentFile(body))
    return {"ok": True}


@api.post("/uploads/{upload_id}/complete")
def complete_upload(request, upload_id: str):
    from .tasks import process_upload

    u = _upload(request, upload_id)
    missing = [n for n in range(u.part_count) if not default_storage.exists(u.part_key(n))]
    if missing:
        raise HttpError(400, f"Missing parts: {missing[:10]}")
    opts = u.layer_options or {}
    s = u.site
    lyr = Layer.objects.create(
        site=s, name=u.layer_name, kind=u.kind, status="processing", z_order=_next_z(s, u.kind),
        attribution=opts.get("attribution", ""),
        captured_at=date.fromisoformat(opts["captured_at"]) if opts.get("captured_at") else None,
        style={"preset": "risa"} if u.kind == "vector" else {"opacity": 1},
    )
    process_upload.defer(upload_id=str(u.id), layer_id=str(lyr.id))
    return layer_dict(lyr)


# ---- Kobo ---------------------------------------------------------------------------


class KoboCreds(Schema):
    server: str
    token: str


class KoboConnect(KoboCreds):
    asset_uid: str
    name: str = ""


class KoboPatch(Schema):
    field_map: dict | None = None
    auto_sync: bool | None = None


@api.post("/responses/{slug}/kobo/projects")
def kobo_projects(request, slug: str, data: KoboCreds):
    r = get_object_or_404(Response, slug=slug)
    require_edit(request, r)
    server = kobo.check_server(data.server)
    return kobo.list_projects(server, data.token.strip())


@api.post("/sites/{site_id}/kobo")
def kobo_connect(request, site_id: str, data: KoboConnect):
    from .tasks import sync_kobo

    s = _site(request, site_id)
    server = kobo.check_server(data.server)
    token = data.token.strip()
    asset = kobo.get_asset(server, token, data.asset_uid)
    questions = kobo.form_questions(asset)
    with transaction.atomic():
        lyr = Layer.objects.create(site=s, name=data.name or asset.get("name") or data.asset_uid, kind="kobo",
                                   status="processing", z_order=_next_z(s), style={"preset": "risa"},
                                   attribution="Field data: KoboCollect direct observation")
        src = KoboSource.objects.create(layer=lyr, server_url=server, asset_uid=data.asset_uid,
                                        asset_name=asset.get("name", ""), token_encrypted=kobo.encrypt_token(token),
                                        field_map=kobo.guess_field_map(questions))
    sync_kobo.defer(source_id=src.id, full=True)
    return layer_dict(lyr)


@api.get("/layers/{layer_id}/kobo")
def kobo_detail(request, layer_id: str):
    lyr = _layer(request, layer_id)
    src = get_object_or_404(KoboSource, layer=lyr)
    asset = kobo.get_asset(src.server_url, kobo.decrypt_token(src.token_encrypted), src.asset_uid)
    return {"field_map": src.field_map, "questions": kobo.form_questions(asset), "auto_sync": src.auto_sync,
            "last_synced_at": src.last_synced_at, "last_error": src.last_error}


@api.patch("/layers/{layer_id}/kobo")
def kobo_patch(request, layer_id: str, data: KoboPatch):
    from .tasks import sync_kobo

    lyr = _layer(request, layer_id)
    src = get_object_or_404(KoboSource, layer=lyr)
    d = data.dict(exclude_unset=True)
    if "auto_sync" in d:
        src.auto_sync = d["auto_sync"]
    if d.get("field_map") is not None:
        src.field_map = {**src.field_map, **d["field_map"]}
        src.save()
        # Re-apply the mapping to every submission
        sync_kobo.defer(source_id=src.id, full=True)
    src.save()
    return {"ok": True}


@api.post("/layers/{layer_id}/kobo/sync")
def kobo_sync(request, layer_id: str):
    from .tasks import sync_kobo

    lyr = _layer(request, layer_id)
    src = get_object_or_404(KoboSource, layer=lyr)
    sync_kobo.defer(source_id=src.id)
    return {"ok": True}


@api.get("/layers/{layer_id}/kobo/photo")
def kobo_photo(request, layer_id: str, url: str):
    lyr = _layer(request, layer_id, edit=False)
    src = get_object_or_404(KoboSource, layer=lyr)
    r = kobo.attachment(src, url)
    out = HttpResponse(r.content, content_type=r.headers.get("content-type", "image/jpeg"))
    out["Cache-Control"] = "private, max-age=86400"
    return out


# ---- products -----------------------------------------------------------------------


class ProductIn(Schema):
    title: str = "Common Operational Picture"
    code: str = ""
    version_label: str = "Initial assessment · v1.0"
    page_size: str = "A3"
    view: dict = {}
    key_message: str = ""
    authority: str = ""


class ProductPatch(Schema):
    title: str | None = None
    code: str | None = None
    version_label: str | None = None
    page_size: str | None = None
    view: dict | None = None
    key_message: str | None = None
    glance: list | None = None
    authority: str | None = None
    sources: str | None = None
    disclaimer: str | None = None
    credits: str | None = None


def _product(request, pid, edit=True) -> Product:
    p = get_object_or_404(Product.objects.select_related("site__response"), id=pid)
    (require_edit if edit else require_view)(request, p.site.response)
    return p


@api.post("/sites/{site_id}/products")
def create_product(request, site_id: str, data: ProductIn):
    s = _site(request, site_id)
    p = Product.objects.create(site=s, **data.dict())
    return product_dict(p)


@api.get("/products/{pid}")
def get_product(request, pid: str, v: int | None = None):
    """Everything the print route needs. With ?v=n, the product as it was rendered."""
    p = _product(request, pid, edit=False)
    data = product_dict(p)
    summary = None
    if v:
        ver = get_object_or_404(ProductVersion, product=p, n=v)
        data = {**data, **ver.snapshot.get("product", {}), "versions": data["versions"]}
        summary = ver.snapshot.get("summary")
    return {"product": data, "site": _site_full(request, p.site), "summary": summary}


@api.patch("/products/{pid}")
def patch_product(request, pid: str, data: ProductPatch):
    p = _product(request, pid)
    for k, val in data.dict(exclude_unset=True).items():
        setattr(p, k, val)
    p.save()
    return product_dict(p)


@api.delete("/products/{pid}")
def delete_product(request, pid: str):
    p = _product(request, pid)
    p.delete()
    return {"ok": True}


@api.post("/products/{pid}/render")
def render_product(request, pid: str):
    from .tasks import render_product as job

    p = _product(request, pid)
    layer_ids = [lyr["id"] for lyr in p.view.get("layers", []) if lyr.get("visible", True)] or None
    snap = {"product": {k: val for k, val in product_dict(p).items() if k not in ("versions", "updated_at", "preview")},
            "summary": site_summary(p.site, layer_ids)}
    snap = json.loads(json.dumps(snap, default=str))
    with transaction.atomic():
        n = (p.versions.aggregate(m=Max("n"))["m"] or 0) + 1
        ver = ProductVersion.objects.create(product=p, n=n, snapshot=snap)
    job.defer(version_id=ver.id)
    return version_dict(ver)


@api.post("/products/{pid}/preview")
def preview_product(request, pid: str):
    """Draft render of page 1 with the current settings, as a low-resolution PNG."""
    from .tasks import render_preview

    p = _product(request, pid)
    p.preview_status, p.preview_error = "processing", ""
    p.save(update_fields=["preview_status", "preview_error"])
    render_preview.defer(product_id=str(p.id))
    return {"ok": True}


@api.get("/products/{pid}/preview.png")
def preview_png(request, pid: str, t: str = ""):
    p = _product(request, pid, edit=False)
    if not p.preview_key:
        raise HttpError(404, "No preview yet")
    if storage.is_s3():
        return HttpResponseRedirect(storage.url(p.preview_key))
    return FileResponse(default_storage.open(p.preview_key, "rb"), content_type="image/png")


@api.get("/products/{pid}/versions/{n}/pdf")
def version_pdf(request, pid: str, n: int):
    p = _product(request, pid, edit=False)
    ver = get_object_or_404(ProductVersion, product=p, n=n)
    if not ver.pdf_key:
        raise HttpError(404, "Not rendered yet")
    if storage.is_s3():
        return HttpResponseRedirect(storage.url(ver.pdf_key))
    return FileResponse(default_storage.open(ver.pdf_key, "rb"), content_type="application/pdf",
                        filename=os.path.basename(ver.pdf_key))
