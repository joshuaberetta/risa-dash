"""
Turn uploads into layers.

Raster: any GeoTIFF becomes a Web Mercator COG on the GoogleMapsCompatible tiling
scheme, which the browser reads directly with range requests (no tile server).
Vector: anything OGR reads (GeoJSON, GeoPackage, zipped Shapefile, KML, CSV with
lat/lon) becomes features in PostGIS.
"""

import json
import logging
import os
import subprocess
import tempfile
from datetime import date

from django.contrib.gis.db.models import Extent
from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction

from . import storage
from .models import Feature, Layer, Upload
from .symbology import classify

log = logging.getLogger(__name__)

RASTER_EXT = (".tif", ".tiff", ".geotiff", ".jp2", ".img", ".vrt")
VECTOR_EXT = (".geojson", ".json", ".gpkg", ".zip", ".kml", ".kmz", ".csv", ".fgb", ".shp", ".gml")
GDAL_ENV = {**os.environ, "GDAL_CACHEMAX": os.environ.get("GDAL_CACHEMAX", "512"), "GDAL_NUM_THREADS": "ALL_CPUS"}


class IngestError(Exception):
    pass


def run(cmd: list[str]) -> str:
    log.info("$ %s", " ".join(cmd))
    p = subprocess.run(cmd, capture_output=True, text=True, env=GDAL_ENV)
    if p.returncode != 0:
        raise IngestError((p.stderr or p.stdout).strip()[-2000:])
    return p.stdout


def kind_for(filename: str) -> str:
    f = filename.lower()
    if f.endswith(RASTER_EXT):
        return "raster"
    if f.endswith(VECTOR_EXT):
        return "vector"
    raise IngestError(f"Can't tell what {filename} is. Upload a GeoTIFF, or GeoJSON, GeoPackage, zipped Shapefile, KML or CSV.")


def process_upload(upload: Upload, layer: Layer) -> None:
    suffix = os.path.splitext(upload.filename)[1].lower() or ".bin"
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, f"source{suffix}")
        storage.concat_parts([upload.part_key(n) for n in range(upload.part_count)], src)
        if os.path.getsize(src) != upload.size:
            raise IngestError("The upload is incomplete")
        # Keep the original for download and re-processing
        layer.original = storage.save(f"layers/{layer.id}/original{suffix}", src)
        if upload.kind == "raster":
            ingest_raster(layer, src, tmp)
        else:
            ingest_vector(layer, src)
    storage.delete_prefix(f"uploads/{upload.id}")
    upload.completed = True
    upload.save(update_fields=["completed"])


# ---- raster -------------------------------------------------------------------------


def ingest_raster(layer: Layer, src: str, tmp: str) -> None:
    info = json.loads(run(["gdalinfo", "-json", src]))
    bands = info.get("bands", [])
    if not info.get("coordinateSystem", {}).get("wkt"):
        raise IngestError("The image has no coordinate system. Export it from your drone software as a GeoTIFF.")
    nb = len(bands)
    has_alpha = any(b.get("colorInterpretation") == "Alpha" for b in bands)
    cog = os.path.join(tmp, "cog.tif")
    cmd = ["gdal_translate", "-of", "COG", "-co", "TILING_SCHEME=GoogleMapsCompatible", "-co", "BLOCKSIZE=256",
           "-co", "OVERVIEWS=IGNORE_EXISTING", "-co", "BIGTIFF=IF_SAFER", "-co", "NUM_THREADS=ALL_CPUS"]
    if nb >= 3 and bands[0].get("type") == "Byte":
        # Imagery: JPEG, with the alpha GDAL adds on reprojection written as a lossless
        # 1-bit mask, which the browser's COG reader uses for transparency.
        cmd += ["-co", "COMPRESS=JPEG", "-co", "QUALITY=85", "-co", "RESAMPLING=BILINEAR"]
        if nb > 4:
            cmd += ["-b", "1", "-b", "2", "-b", "3"] + (["-b", str(next(i + 1 for i, b in enumerate(bands) if b.get("colorInterpretation") == "Alpha"))] if has_alpha else [])
    else:
        cmd += ["-co", "COMPRESS=DEFLATE", "-co", "PREDICTOR=2", "-co", "RESAMPLING=BILINEAR"]
    first_mask = (bands[0].get("mask") or {}).get("flags", ["ALL_VALID"]) if bands else []
    if nb == 3 and not has_alpha and first_mask == ["ALL_VALID"] and bands[0].get("noDataValue") is None:
        # Drone exports often have a black collar with no nodata or mask, and lossy
        # compression means it isn't exactly 0. nearblack walks in from the edges and
        # makes the near-black collar transparent, leaving dark pixels inside alone.
        masked = os.path.join(tmp, "masked.tif")
        run(["nearblack", "-q", "-setalpha", "-near", "15", "-of", "GTiff", "-co", "TILED=YES",
             "-co", "COMPRESS=ZSTD", "-co", "BIGTIFF=IF_SAFER", "-o", masked, src])
        src = masked
    run([*cmd, src, cog])
    out = json.loads(run(["gdalinfo", "-json", cog]))
    layer.bbox = _wgs84_bbox(out) or _wgs84_bbox(info)
    # Ground resolution of the source, in cm, when it's in metres
    gt = info.get("geoTransform")
    wkt = info.get("coordinateSystem", {}).get("wkt", "")
    projected = wkt.startswith(("PROJCRS", "PROJCS"))
    if gt and projected and "metre" in wkt:
        layer.resolution_cm = round(abs(gt[1]) * 100, 1)
    md = (info.get("metadata") or {}).get("", {})
    dt = md.get("TIFFTAG_DATETIME", "")
    if dt[:10].replace(":", "-").count("-") == 2 and not layer.captured_at:
        try:
            layer.captured_at = date.fromisoformat(dt[:10].replace(":", "-"))
        except ValueError:
            pass
    layer.source = storage.save(f"layers/{layer.id}/cog.tif", cog, public=True, content_type="image/tiff")
    layer.status = "ready"
    layer.error = ""
    layer.save()


def _wgs84_bbox(info: dict):
    ext = info.get("wgs84Extent", {}).get("coordinates")
    if not ext:
        return None
    xs = [p[0] for p in ext[0]]
    ys = [p[1] for p in ext[0]]
    return [min(xs), min(ys), max(xs), max(ys)]


# ---- vector -------------------------------------------------------------------------


def _ogr_path(src: str) -> str:
    low = src.lower()
    if low.endswith(".zip"):
        return f"/vsizip/{src}"
    if low.endswith(".kmz"):
        return f"/vsizip/{src}"
    return src


def ingest_vector(layer: Layer, src: str) -> None:
    path = _ogr_path(src)
    open_opts = []
    if src.lower().endswith(".csv"):
        open_opts = ["-oo", "X_POSSIBLE_NAMES=lon*,lng*,long*,x,easting", "-oo", "Y_POSSIBLE_NAMES=lat*,y,northing",
                     "-oo", "KEEP_GEOM_COLUMNS=NO", "-oo", "AUTODETECT_TYPE=YES"]
    info = json.loads(run(["ogrinfo", "-json", "-so", *open_opts, path]))
    names = [lyr["name"] for lyr in info.get("layers", [])]
    if not names:
        raise IngestError("No layers found in the file")
    count = 0
    with tempfile.TemporaryDirectory() as tmp, transaction.atomic():
        layer.features.all().delete()
        for name in names:
            out = os.path.join(tmp, f"{len(os.listdir(tmp))}.geojsonl")
            run(["ogr2ogr", "-f", "GeoJSONSeq", "-t_srs", "EPSG:4326", "-dim", "XY", "-makevalid",
                 *open_opts, out, path, name])
            batch = []
            with open(out) as f:
                for line in f:
                    line = line.strip().lstrip("\x1e")
                    if not line:
                        continue
                    feat = json.loads(line)
                    if not feat.get("geometry"):
                        continue
                    props = feat.get("properties") or {}
                    if len(names) > 1:
                        props["_source_layer"] = name
                    rtype, rstatus, label = classify(props)
                    batch.append(Feature(
                        layer=layer, geom=GEOSGeometry(json.dumps(feat["geometry"]), srid=4326), properties=props,
                        risa_type=rtype, risa_status=rstatus, label=label,
                        source_ref=str(feat.get("id", "")),
                    ))
                    if len(batch) >= 2000:
                        Feature.objects.bulk_create(batch)
                        count += len(batch)
                        batch = []
            Feature.objects.bulk_create(batch)
            count += len(batch)
    if count == 0:
        raise IngestError("The file has no features with a geometry")
    ext = layer.features.aggregate(e=Extent("geom"))["e"]
    layer.bbox = list(ext) if ext else None
    layer.status = "ready"
    layer.error = ""
    layer.save()
