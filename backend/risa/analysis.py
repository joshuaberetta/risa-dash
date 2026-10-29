"""
Imagery analysis for a site: find shelters and buildings on an orthomosaic, then
group shelters into blocks and draw the site boundary.

SIMULATED. This stands in for a segmentation model (see plans/mvp.md, "Imagery
analysis"). It uses colour rules on the real image: bright white and blue tarps are
shelter candidates, large bright roofs are buildings. That's crude, but the outlines
sit on real objects, so the review workflow (suggested -> accepted / rejected /
edited) can be built and tried before a model is plugged in. Every feature carries
`simulated: true` and the model name, and nothing counts until a person accepts it.

A real model replaces `detect()`: same input (an RGB array for the area of interest
plus its geotransform), same output (polygons with a class and a confidence).
"""

import json
import logging
import math
import os
import subprocess
import tempfile
import time

import numpy as np
from django.contrib.gis.geos import GEOSGeometry
from django.db import connection, transaction

from . import storage
from .ingest import GDAL_ENV, IngestError, run
from .models import Feature, Layer

log = logging.getLogger(__name__)

MODEL = "simulated-colour-rules-v0"
GSD = 0.25           # metres per pixel for the analysis
MAX_PIXELS = 30_000_000
SHELTER_M2 = (3.5, 60)
BUILDING_M2 = (60, 2500)


def progress(layer: Layer, step: str, pct: int) -> None:
    layer.meta = {**layer.meta, "progress": {"step": step, "pct": pct}}
    layer.save(update_fields=["meta", "updated_at"])


# ---- image -> arrays --------------------------------------------------------------


def read_aoi(cog_path: str, bounds: list[float], tmp: str) -> tuple[np.ndarray, np.ndarray, dict]:
    """RGB and mask for the area of interest, resampled to about GSD m/px.
    Returns (rgb[h, w, 3], valid[h, w], georef) where georef has the ENVI header path."""
    w, s, e, n = bounds
    # Ground metres to Web Mercator units at this latitude
    k = 1 / math.cos(math.radians((s + n) / 2))
    tr = GSD * k
    # Size in Web Mercator units; coarsen big areas to stay within memory
    R = 6378137.0
    mw = math.radians(abs(e - w)) * R
    mh = abs(math.log(math.tan(math.pi / 4 + math.radians(n) / 2)) - math.log(math.tan(math.pi / 4 + math.radians(s) / 2))) * R
    px = (mw / tr) * (mh / tr)
    if px > MAX_PIXELS:
        tr *= math.sqrt(px / MAX_PIXELS)
    out = os.path.join(tmp, "aoi.img")
    # BSQ explicitly: ENVI otherwise keeps the source's pixel interleaving
    run(["gdal_translate", "-q", "-of", "ENVI", "-co", "INTERLEAVE=BSQ", "-projwin_srs", "EPSG:4326", "-projwin", str(w), str(n), str(e), str(s),
         "-tr", str(tr), str(tr), "-r", "average", "-b", "1", "-b", "2", "-b", "3", "-b", "mask", cog_path, out])
    info = json.loads(run(["gdalinfo", "-json", out]))
    W, H = info["size"]
    raw = np.fromfile(out, dtype=np.uint8)
    if raw.size != W * H * 4:
        raise IngestError("Couldn't read the image for analysis")
    bands = raw.reshape(4, H, W)
    rgb = np.moveaxis(bands[:3], 0, -1)
    return rgb, bands[3] > 0, {"path": out, "W": W, "H": H, "tr": tr, "k": k, "gt": info["geoTransform"]}


# ---- detection (the part a model replaces) ------------------------------------------


def _shift_min(a: np.ndarray) -> np.ndarray:
    o = a.copy()
    o[1:] &= a[:-1]; o[:-1] &= a[1:]; o[:, 1:] &= a[:, :-1]; o[:, :-1] &= a[:, 1:]  # noqa: E702
    return o


def _shift_max(a: np.ndarray) -> np.ndarray:
    o = a.copy()
    o[1:] |= a[:-1]; o[:-1] |= a[1:]; o[:, 1:] |= a[:, :-1]; o[:, :-1] |= a[:, 1:]  # noqa: E702
    return o


DEFAULT_RULES = {"grey_min": 135, "sat_max": 0.13, "shelter_m2": list(SHELTER_M2)}


def detect(rgb: np.ndarray, valid: np.ndarray, rules: dict | None = None) -> np.ndarray:
    """Candidate mask: tarps and bright roofs. Returns uint8 (1 = candidate)."""
    rules = {**DEFAULT_RULES, **(rules or {})}
    c = rgb.astype(np.int16)
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    mx = c.max(axis=-1)
    mn = c.min(axis=-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    # Tarps and sheet-metal roofs are bright and grey; bare ground is tan (red over blue)
    grey = (mx > rules["grey_min"]) & (sat < rules["sat_max"]) & (r - b < 14)
    blue = (b > 105) & (b > r + 28) & (b > g + 6)
    m = (grey | blue) & valid
    # Opening removes speckle and closing fills each roof; one more erosion splits
    # roofs that touch (outlines are grown back by a pixel when classifying)
    m = _shift_max(_shift_min(m))
    m = _shift_min(_shift_max(m))
    m = _shift_min(m)
    return m.astype(np.uint8)


def score(area_m2: float, compactness: float, cls: str) -> float:
    """Pseudo-confidence: how tent-like (or roof-like) the shape is. Simulated."""
    if cls == "shelter":
        size = math.exp(-((math.log(max(area_m2, 1)) - math.log(16)) ** 2) / 1.2)
    else:
        size = 0.75
    return round(max(0.05, min(0.98, 0.25 + 0.45 * size + 0.3 * compactness)), 2)


# ---- vectorise and store ----------------------------------------------------------


def polygonise(mask: np.ndarray, georef: dict, tmp: str) -> list[dict]:
    mask_path = os.path.join(tmp, "mask.img")
    # A one-band copy of the AOI's header gives the mask the same georeferencing
    run(["gdal_translate", "-q", "-of", "ENVI", "-b", "1", georef["path"], mask_path])
    mask.tofile(mask_path)
    out = os.path.join(tmp, "polys.geojson")
    p = subprocess.run(["gdal", "raster", "polygonize", "--connect-diagonal-pixels", "--nln", "polys",
                        "--attribute-name", "dn", mask_path, out], capture_output=True, text=True, env=GDAL_ENV)
    if p.returncode != 0:
        raise IngestError(p.stderr[-1500:])
    seq = os.path.join(tmp, "polys4326.geojsonl")
    run(["ogr2ogr", "-f", "GeoJSONSeq", "-t_srs", "EPSG:4326", "-where", "dn = 1", "-simplify", str(georef["tr"] * 0.9),
         seq, out])
    with open(seq) as f:
        return [json.loads(line.lstrip("\x1e")) for line in f if line.strip()]


def sample_colour(rgb: np.ndarray, georef: dict, x: float, y: float) -> tuple[float, float, float]:
    """Brightness, saturation and blue-ness around a point (Web Mercator x, y)."""
    gt = georef["gt"]
    col, row = int((x - gt[0]) / gt[1]), int((y - gt[3]) / gt[5])
    win = rgb[max(0, row - 2): row + 3, max(0, col - 2): col + 3].reshape(-1, 3).astype(float)
    if not len(win):
        return 0.0, 0.0, 0.0
    m = win.mean(axis=0)
    mx, mn = m.max(), m.min()
    return round(mx / 255, 3), round((mx - mn) / max(mx, 1), 3), round((m[2] - m[0]) / 255, 3)


def candidate_stats(merc, rgb: np.ndarray, georef: dict) -> dict:
    """What the learned detector looks at for each candidate."""
    a = merc.area / georef["k"] ** 2
    perim = merc.length / georef["k"]
    x0, y0, x1, y1 = merc.extent
    p = merc.point_on_surface
    bright, sat, blue = sample_colour(rgb, georef, p.x, p.y)
    return {"area_m2": round(a, 1), "compact": round(min(1.0, 4 * math.pi * a / max(perim**2, 1e-6)), 3),
            "aspect": round(min(x1 - x0, y1 - y0) / max(x1 - x0, y1 - y0, 1e-9), 3),
            "bright": bright, "sat": sat, "blue": blue}


FEATURES = ("log_area", "compact", "aspect", "bright", "sat", "blue")


def vector(st: dict) -> list[float]:
    return [math.log(max(st["area_m2"], 0.5)), st["compact"], st["aspect"], st["bright"], st["sat"], st["blue"]]


def learned_confidence(st: dict, params: dict) -> float:
    x = (np.array(vector(st)) - np.array(params["mean"])) / np.array(params["scale"])
    return float(1 / (1 + math.exp(-(float(x @ np.array(params["weights"])) + params["bias"]))))


def classify(feats: list[dict], georef: dict, rgb: np.ndarray, detector=None) -> list[tuple[GEOSGeometry, str, float, float, dict]]:
    rules = {**DEFAULT_RULES, **((detector.params.get("rules") if detector else None) or {})}
    lo, hi = rules["shelter_m2"]
    out = []
    for f in feats:
        # Grow back the pixel the last erosion took off
        merc = GEOSGeometry(json.dumps(f["geometry"]), srid=4326).transform(3857, clone=True).buffer(georef["tr"], 2)
        st = candidate_stats(merc, rgb, georef)
        a = st["area_m2"]
        if lo <= a < hi:
            cls = "shelter"
        elif BUILDING_M2[0] <= a < BUILDING_M2[1] and st["compact"] > 0.35:
            cls = "building"
        else:
            continue
        if detector and cls == "shelter":
            conf = round(learned_confidence(st, detector.params), 2)
            # The learned detector also drops what people consistently rejected
            if conf < detector.params.get("drop_below", 0.15):
                continue
        else:
            conf = score(a, st["compact"], cls)
        out.append((merc.transform(4326, clone=True), cls, a, conf, st))
    return out


def derive_blocks(layer: Layer, lat: float, model: str = MODEL) -> int:
    """Group shelters into blocks (DBSCAN on centroids) and outline the site."""
    sql_blocks = """
        WITH s AS (
            SELECT geom, ST_ClusterDBSCAN(ST_Transform(ST_Centroid(geom), 3857), eps := %s, minpoints := 6) OVER () AS c
            FROM risa_feature WHERE layer_id = %s AND risa_type = 'shelter'
        )
        SELECT c, count(*), ST_AsGeoJSON(ST_Transform(ST_Buffer(ST_ConcaveHull(ST_Collect(ST_Transform(ST_PointOnSurface(geom), 3857)), 0.3), %s), 4326))
        FROM s WHERE c IS NOT NULL GROUP BY c HAVING count(*) >= 25 ORDER BY count(*) DESC
    """
    sql_boundary = """
        SELECT ST_AsGeoJSON(ST_Transform(ST_Buffer(ST_ConcaveHull(ST_Collect(ST_Transform(ST_PointOnSurface(geom), 3857)), 0.2), %s), 4326)), count(*)
        FROM risa_feature WHERE layer_id = %s AND risa_type = 'shelter'
    """
    # Shelters within 14 ground metres of six others form a block (Web Mercator units)
    eps = 14 / math.cos(math.radians(lat))
    rows = []
    with connection.cursor() as cur:
        # Hulls of the shelters' centres, grown to cover the shelters themselves
        cur.execute(sql_blocks, [eps, str(layer.id), eps * 0.3])
        rows = cur.fetchall()
        cur.execute(sql_boundary, [eps * 0.5, str(layer.id)])
        boundary = cur.fetchone()
    feats = [
        Feature(layer=layer, geom=GEOSGeometry(gj, srid=4326), risa_type="block", label=f"Block {i + 1} · {n} shelters",
                properties={"ai_class": "block", "shelters": n, "confidence": 0.6, "review": "suggested",
                            "model": model, "simulated": True})
        for i, (_, n, gj) in enumerate(rows)
    ]
    if boundary and boundary[0] and boundary[1] >= 12:
        feats.append(Feature(layer=layer, geom=GEOSGeometry(boundary[0], srid=4326), risa_type="boundary",
                             label="Site boundary (detected)",
                             properties={"ai_class": "boundary", "shelters": boundary[1], "confidence": 0.55,
                                         "review": "suggested", "model": model, "simulated": True}))
    Feature.objects.bulk_create(feats)
    return len(rows)


def latest_detector(response):
    from .models import Detector

    return Detector.objects.filter(response=response, status="ready").order_by("-version").first()


def analyse(layer: Layer) -> None:
    src = Layer.objects.get(id=layer.meta["source_layer"])
    bounds = layer.meta["aoi"]
    detector = latest_detector(layer.site.response)
    model = detector.name if detector else MODEL
    layer.meta = {**layer.meta, "model": model, "detector_version": detector.version if detector else 0}
    with tempfile.TemporaryDirectory() as tmp:
        progress(layer, "Reading the imagery", 10)
        with storage.local_copy(src.source, suffix=".tif") as cog:
            rgb, valid, georef = read_aoi(cog, bounds, tmp)
        progress(layer, "Finding shelters and roofs", 35)
        mask = detect(rgb, valid, detector.params.get("rules") if detector else None)
        # A model takes longer; keep the simulation honest about the wait, roughly
        time.sleep(1.5)
        progress(layer, "Tracing outlines", 60)
        polys = polygonise(mask, georef, tmp)
        found = classify(polys, georef, rgb, detector)
    progress(layer, "Grouping into blocks", 80)
    with transaction.atomic():
        layer.features.all().delete()
        Feature.objects.bulk_create([
            Feature(layer=layer, geom=g, risa_type=cls, label="",
                    properties={"ai_class": cls, "area_m2": a, "confidence": conf, "review": "suggested",
                                "model": model, "simulated": True, "stats": st})
            for g, cls, a, conf, st in found
        ])
        blocks = derive_blocks(layer, (bounds[1] + bounds[3]) / 2, model)
    counts = {"shelter": sum(1 for x in found if x[1] == "shelter"),
              "building": sum(1 for x in found if x[1] == "building"), "block": blocks}
    from django.contrib.gis.db.models import Extent

    ext = layer.features.aggregate(e=Extent("geom"))["e"]
    layer.bbox = list(ext) if ext else bounds
    layer.meta = {**layer.meta, "counts": counts, "progress": {"step": "Done", "pct": 100}}
    layer.status = "ready"
    layer.error = ""
    layer.save()
