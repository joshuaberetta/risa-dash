"""Response bundles: a whole response in one zip, to move it between instances (cloud →
box → cloud, by USB or a link) and to archive it.

    manifest.json               format, version, the response, and every other file with its
                                SHA-256 and size. Written last, so a cut-off copy has none.
    response.json               the response, sites, layers, Kobo field maps (no tokens),
                                products and their versions, logos, detector versions
    features/<layer>.geojson    each vector layer's features, with their IDs
    files/<storage key>         COGs, rendered PDFs, logos, vector originals (and imagery
                                originals when asked)
    gpkg/<response>_<site>.gpkg each site's GeoPackage, for QGIS and ArcGIS

Import merges by UUID: rows in the bundle are created or updated, rows that aren't are
kept, and each vector layer's features are replaced by the bundle's. Importing the same
bundle again changes nothing. Imagery can be left out (`imagery=False`) to send only the
work done on it.
"""

import datetime
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
import zipfile

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.text import slugify

from . import exports, storage
from .models import Detector, Feature, KoboSource, Layer, Logo, Product, ProductVersion, Response, Site

FORMAT, VERSION = "risa-bundle", 1
VECTOR_KINDS = ("vector", "kobo", "annotations", "analysis")
# Storage keys a bundle may write: under the prefix of the row they belong to
KEY_RE = re.compile(r"^(layers|products|logos)/[0-9a-f-]{36}/(?!\.)[^/\\]+$")


class BundleError(Exception):
    pass


class OlderBundle(BundleError):
    """The bundle predates changes made here since the last import, or a bundle already
    imported: importing it would undo them. Allowed when the person confirms."""


# ---- rows ---------------------------------------------------------------------------


def _row(obj: models.Model, exclude: tuple = ()) -> dict:
    """A model instance as JSON-safe values, by column (`site_id`, not `site`)."""
    out = {}
    for f in obj._meta.concrete_fields:
        if f.attname in exclude:
            continue
        v = getattr(obj, f.attname)
        if isinstance(v, GEOSGeometry):
            v = v.ewkt
        elif isinstance(v, uuid.UUID):
            v = str(v)
        elif isinstance(v, datetime.date | datetime.datetime):
            v = v.isoformat()
        out[f.attname] = v
    return out


def _clean(model, row: dict) -> dict:
    """The bundle's values for model's columns only, with geometries parsed."""
    cols = {f.attname: f for f in model._meta.concrete_fields}
    out = {}
    for k, v in row.items():
        if k not in cols:
            continue
        if isinstance(cols[k], models.GeometryField) and v:
            v = GEOSGeometry(v)
        out[k] = v
    return out


def _upsert(model, row: dict, key: tuple = ("id",)) -> bool:
    """Update the row with the same key, or create it keeping its created_at. True if created."""
    lookup = {k: row[k] for k in key}
    values = {k: v for k, v in row.items() if k not in key and k != "id"}
    if model.objects.filter(**lookup).update(**values):
        return False
    model.objects.create(**row)
    if "created_at" in row:
        model.objects.filter(**lookup).update(created_at=row["created_at"])
    return True


# ---- export -------------------------------------------------------------------------


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def export_bundle(response: Response, out_path: str, imagery: bool = True, originals: bool = False) -> dict:
    """Write the response's bundle to out_path. Returns the manifest."""
    layers = [lyr for lyr in Layer.objects.filter(site__response=response, status="ready").select_related("site")
              if imagery or lyr.kind != "raster"]
    keys: list[str] = []
    for lyr in layers:
        if lyr.kind == "raster" and lyr.source:
            keys.append(lyr.source)
        if lyr.original and (originals or lyr.is_vector):
            keys.append(lyr.original)
    products = Product.objects.filter(site__response=response)
    versions = ProductVersion.objects.filter(product__site__response=response, status="ready")
    logos = Logo.objects.filter(response=response)
    keys += [v.pdf_key for v in versions if v.pdf_key] + [lg.key for lg in logos if lg.key]

    data = {
        # When it last took a bundle is this instance's business, not the next one's
        "response": _row(response, exclude=("bundle_at", "bundle_imported_at")),
        "sites": [_row(s) for s in response.sites.all()],
        "layers": [_row(lyr, exclude=("error",)) for lyr in layers],
        "kobo": [_row(k, exclude=("id", "token_encrypted", "last_submission_id", "last_error"))
                 for k in KoboSource.objects.filter(layer__in=[lyr for lyr in layers if lyr.kind == "kobo"])],
        "products": [_row(p, exclude=("preview_key", "preview_status", "preview_error", "preview_at")) for p in products],
        "versions": [_row(v, exclude=("id",)) for v in versions],
        "logos": [_row(lg) for lg in logos],
        "detectors": [_row(d, exclude=("id",)) for d in Detector.objects.filter(response=response, status="ready")],
    }
    files: dict[str, dict] = {}

    with zipfile.ZipFile(out_path, "w", allowZip64=True) as z, tempfile.TemporaryDirectory() as tmp:

        def add(name: str, path: str, compress: bool = True):
            files[name] = {"sha256": _sha256(path), "size": os.path.getsize(path)}
            z.write(path, name, compress_type=zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED)

        def add_json(name: str, obj):
            path = os.path.join(tmp, "out.json")
            with open(path, "w") as f:
                json.dump(obj, f, ensure_ascii=False, default=str)
            add(name, path)

        add_json("response.json", data)
        for lyr in layers:
            if lyr.is_vector:
                add_json(f"features/{lyr.id}.geojson", _features(lyr))
        for key in dict.fromkeys(keys):
            if not default_storage.exists(key):
                continue
            with storage.local_copy(key) as path:
                # COGs and PDFs are compressed already
                add(f"files/{key}", path, compress=not key.endswith((".tif", ".pdf", ".png", ".jpg", ".zip")))
        for s in response.sites.all():
            gpkg = os.path.join(tmp, f"{response.slug}_{s.slug}.gpkg")
            exports.site_geopackage(s, gpkg)
            if os.path.exists(gpkg):
                add(f"gpkg/{os.path.basename(gpkg)}", gpkg)

        manifest = {
            "format": FORMAT, "version": VERSION, "created_at": timezone.now().isoformat(),
            "instance": settings.PUBLIC_URL, "imagery": imagery,
            "response": {"id": str(response.id), "slug": response.slug, "name": response.name},
            "files": files,
        }
        z.writestr("manifest.json", json.dumps(manifest, indent=1, ensure_ascii=False))
    return manifest


def _features(layer: Layer) -> dict:
    feats = []
    for f in layer.features.all().iterator(chunk_size=2000):
        row = _row(f, exclude=("layer_id", "geom", "updated_at"))
        feats.append({"type": "Feature", "id": row.pop("id"), "geometry": json.loads(f.geom.geojson), "properties": row})
    return {"type": "FeatureCollection", "features": feats}


# ---- import -------------------------------------------------------------------------


def read_manifest(z: zipfile.ZipFile) -> dict:
    try:
        m = json.loads(z.read("manifest.json"))
    except KeyError:
        raise BundleError("Not a complete bundle: manifest.json is missing (the copy may have been cut off)") from None
    except ValueError as e:
        raise BundleError(f"manifest.json is not valid: {e}") from None
    if m.get("format") != FORMAT:
        raise BundleError("Not a RISA Dashboard bundle")
    if m.get("version", 0) > VERSION:
        raise BundleError(f"This bundle is format version {m['version']}; update this instance to import it")
    return m


def verify(z: zipfile.ZipFile, manifest: dict) -> None:
    """Every file listed is present with its checksum, and nothing else needs trusting."""
    names = set(z.namelist())
    for name, info in manifest["files"].items():
        if name not in names:
            raise BundleError(f"{name} is missing from the bundle")
        h = hashlib.sha256()
        with z.open(name) as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != info["sha256"]:
            raise BundleError(f"{name} is damaged (checksum does not match); copy the bundle again")
    if "response.json" not in manifest["files"]:
        raise BundleError("response.json is missing from the bundle")


def _owned(key: str, prefix: str, row_id: str) -> bool:
    return bool(key) and bool(KEY_RE.match(key)) and key.startswith(f"{prefix}/{row_id}/")


def local_changed_at(response: Response):
    """When anything of the response last changed here other than by a bundle import."""
    since = response.bundle_imported_at
    after = {"updated_at__gt": since} if since else {}
    stamps = [
        Response.objects.filter(id=response.id, **after).aggregate(m=Max("updated_at"))["m"],
        Site.objects.filter(response=response, **after).aggregate(m=Max("updated_at"))["m"],
        Layer.objects.filter(site__response=response, **after).aggregate(m=Max("updated_at"))["m"],
        Feature.objects.filter(layer__site__response=response, **after).aggregate(m=Max("updated_at"))["m"],
        Product.objects.filter(site__response=response, **after).aggregate(m=Max("updated_at"))["m"],
        ProductVersion.objects.filter(product__site__response=response,
                                      **({"rendered_at__gt": since} if since else {})).aggregate(m=Max("rendered_at"))["m"],
    ]
    return max((t for t in stamps if t), default=None)


def _when(t: datetime.datetime) -> str:
    return timezone.localtime(t).strftime("%d/%m/%Y %H:%M:%S")


def import_bundle(path: str, edit_key_hash: str | None = None, force: bool = False, allow_older: bool = False) -> dict:
    """Import a bundle file. Into a response that exists here, only with its edit key
    (edit_key_hash), unless force (the command line); and only if the bundle is newer than
    what's here, unless allow_older. Returns what was done."""
    with zipfile.ZipFile(path) as z:
        manifest = read_manifest(z)
        verify(z, manifest)
        data = json.loads(z.read("response.json"))
        r_row = data["response"]
        existing = Response.objects.filter(id=r_row["id"]).first()
        if existing and not force and edit_key_hash != existing.edit_key_hash:
            raise BundleError(f'"{existing.name}" is already on this instance; importing into it needs its edit key')
        made = datetime.datetime.fromisoformat(manifest["created_at"])
        if existing and not allow_older:
            newer = [t for t in (existing.bundle_at, local_changed_at(existing)) if t and t > made]
            if newer:
                raise OlderBundle(
                    f"This bundle was made on {_when(made)}, before changes to \"{existing.name}\" here "
                    f"(the latest on {_when(max(newer))}). Importing it would undo them. Make a new bundle where it "
                    "came from, or import this one anyway.")

        # Files first, outside the transaction: a failed import leaves only unused files
        files = {n[len("files/"):] for n in manifest["files"] if n.startswith("files/")}
        for key in files:
            if not KEY_RE.match(key):
                raise BundleError(f"Unexpected file in the bundle: {key}")
        with tempfile.TemporaryDirectory() as tmp:
            for key in files:
                local = os.path.join(tmp, "f")
                with z.open(f"files/{key}") as src, open(local, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                storage.save(key, local, public=key.endswith("/cog.tif"),
                             content_type="image/tiff" if key.endswith(".tif") else None)

        def have(key: str) -> bool:
            return key in files or default_storage.exists(key)

        counts = {"sites": 0, "layers": 0, "features": 0, "products": 0, "versions": 0}
        with transaction.atomic():
            r = _clean(Response, r_row)
            if existing:
                # The local edit key and slug stay
                r.pop("edit_key_hash", None)
                r["slug"] = existing.slug
            else:
                r["slug"] = _free_slug(r["slug"], Response.objects.all())
            created = _upsert(Response, r)
            response = Response.objects.get(id=r["id"])

            for row in data["sites"]:
                row = _clean(Site, {**row, "response_id": str(response.id)})
                other = response.sites.filter(slug=row["slug"]).exclude(id=row["id"])
                local = Site.objects.filter(id=row["id"]).first()
                if local and local.response_id != response.id:
                    raise BundleError(f"Site {row['id']} belongs to another response here")
                row["slug"] = local.slug if local else (_free_slug(row["slug"], response.sites.all()) if other.exists()
                                                        else row["slug"])
                _upsert(Site, row)
                counts["sites"] += 1
            site_ids = {str(i) for i in response.sites.values_list("id", flat=True)}

            for row in data["layers"]:
                if row["site_id"] not in site_ids:
                    raise BundleError(f"Layer {row['id']} is not on a site of this response")
                row = _clean(Layer, row)
                if row["kind"] == "raster" and not (_owned(row["source"], "layers", row["id"]) and have(row["source"])):
                    continue
                if row.get("original") and not (_owned(row["original"], "layers", row["id"]) and have(row["original"])):
                    row["original"] = ""
                if Layer.objects.filter(id=row["id"]).exclude(site_id__in=site_ids).exists():
                    raise BundleError(f"Layer {row['id']} belongs to another response here")
                _upsert(Layer, {**row, "error": ""})
                counts["layers"] += 1
                if row["kind"] in VECTOR_KINDS and f"features/{row['id']}.geojson" in manifest["files"]:
                    counts["features"] += _replace_features(row["id"], json.loads(z.read(f"features/{row['id']}.geojson")))

            for row in data.get("kobo", []):
                row = _clean(KoboSource, row)
                if not Layer.objects.filter(id=row["layer_id"], kind="kobo").exists():
                    continue
                local = KoboSource.objects.filter(layer_id=row["layer_id"]).first()
                if local:
                    # This instance's token and sync position stay
                    KoboSource.objects.filter(id=local.id).update(field_map=row["field_map"], asset_name=row["asset_name"])
                else:
                    KoboSource.objects.create(**{**row, "token_encrypted": "", "auto_sync": False,
                                                 "last_error": "Imported from a bundle without its Kobo token; reconnect to sync"})

            layer_ids = {str(i) for i in Layer.objects.filter(site__response=response).values_list("id", flat=True)}
            for row in data["products"]:
                if row["site_id"] not in site_ids:
                    raise BundleError(f"Product {row['id']} is not on a site of this response")
                row = _clean(Product, row)
                view = row.get("view") or {}
                view["layers"] = [lyr for lyr in view.get("layers", []) if lyr.get("id") in layer_ids]
                _upsert(Product, {**row, "view": view})
                counts["products"] += 1
            product_ids = {str(i) for i in Product.objects.filter(site__response=response).values_list("id", flat=True)}

            for row in data["versions"]:
                if row["product_id"] not in product_ids:
                    continue
                row = _clean(ProductVersion, row)
                if not (_owned(row["pdf_key"], "products", row["product_id"]) and have(row["pdf_key"])):
                    row["pdf_key"], row["status"] = "", "failed"
                    row["error"] = "The PDF was not in the bundle"
                _upsert(ProductVersion, row, key=("product_id", "n"))
                counts["versions"] += 1

            for row in data.get("logos", []):
                row = _clean(Logo, {**row, "response_id": str(response.id)})
                if have(row["key"]) and _owned(row["key"], "logos", row["id"]):
                    _upsert(Logo, row)

            for row in data.get("detectors", []):
                _upsert(Detector, _clean(Detector, {**row, "response_id": str(response.id)}), key=("response_id", "version"))

            # Last, so everything this import wrote is older than bundle_imported_at
            Response.objects.filter(id=response.id).update(
                bundle_at=max(t for t in (existing and existing.bundle_at, made) if t),
                bundle_imported_at=timezone.now())

    return {"response": response.slug, "name": response.name, "created": created, "files": len(files), **counts}


def _replace_features(layer_id: str, fc: dict) -> int:
    Feature.objects.filter(layer_id=layer_id).delete()
    batch = []
    for f in fc["features"]:
        props = _clean(Feature, f["properties"])
        batch.append(Feature(id=f["id"], layer_id=layer_id, geom=GEOSGeometry(json.dumps(f["geometry"]), srid=4326),
                             **{k: v for k, v in props.items() if k not in ("id", "layer_id", "geom")}))
    Feature.objects.bulk_create(batch, batch_size=2000)
    return len(batch)


def _free_slug(slug: str, qs) -> str:
    base = slugify(slug)[:70] or "item"
    out, i = base, 2
    while qs.filter(slug=out).exists():
        out, i = f"{base}-{i}", i + 1
    return out
