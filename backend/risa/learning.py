"""
Learning from people's corrections to the shelter detection.

Every review is a label: accepted, edited and hand-added shelters are positives,
rejected suggestions are negatives. `train()` turns a response's labels into a new
detector version: tighter colour and size rules, and a small logistic model that
re-scores candidates (and drops the kind people keep rejecting). It reports accuracy
on reviews held back from training, next to the built-in rules on the same reviews.

This calibrates the SIMULATED stand-in. A real segmentation model is fine-tuned on
the same labels, exported with `training_data()` (imagery + labels, the format
HOT's fAIr/RAMP training takes). See plans/mvp.md, "Learning from corrections".
"""

import hashlib
import json
import os
import tempfile
import zipfile

import numpy as np
from django.contrib.gis.db.models import Extent
from django.db.models import Max

from . import analysis, storage
from .ingest import run
from .models import Detector, Feature, Layer, Response

MIN_EACH = 20  # positives and negatives needed to train


def labels(response: Response):
    """(feature, label) for every reviewed shelter in the response's analysis layers."""
    qs = Feature.objects.filter(layer__site__response=response, layer__kind="analysis", risa_type="shelter")
    for f in qs.iterator():
        r = f.properties.get("review")
        if r == "accepted":
            yield f, 1
        elif r == "rejected":
            yield f, 0


def counts(response: Response) -> dict:
    pos = neg = added = 0
    for f, y in labels(response):
        pos += y
        neg += 1 - y
        added += bool(f.properties.get("added"))
    return {"positives": pos, "negatives": neg, "added": added, "needed": MIN_EACH}


def _fill_stats(feats: list[Feature]) -> None:
    """Hand-added shelters have no image features yet: sample them from the imagery."""
    missing = [f for f in feats if not f.properties.get("stats")]
    by_layer: dict = {}
    for f in missing:
        by_layer.setdefault(f.layer_id, []).append(f)
    for layer_id, fs in by_layer.items():
        lyr = Layer.objects.get(id=layer_id)
        src = Layer.objects.filter(id=lyr.meta.get("source_layer")).first()
        if not src:
            continue
        ext = Feature.objects.filter(id__in=[f.id for f in fs]).aggregate(e=Extent("geom"))["e"]
        pad = 0.0002
        bounds = [ext[0] - pad, ext[1] - pad, ext[2] + pad, ext[3] + pad]
        with tempfile.TemporaryDirectory() as tmp, storage.local_copy(src.source, suffix=".tif") as cog:
            rgb, _, georef = analysis.read_aoi(cog, bounds, tmp)
            for f in fs:
                st = analysis.candidate_stats(f.geom.transform(3857, clone=True), rgb, georef)
                f.properties = {**f.properties, "stats": st}
                f.save(update_fields=["properties"])


def _held_out(f: Feature) -> bool:
    # Same split every time for the same feature
    return int(hashlib.sha1(str(f.id).encode()).hexdigest(), 16) % 5 == 0


def _fit(X: np.ndarray, y: np.ndarray, l2: float = 0.01, steps: int = 3000, lr: float = 0.3):
    # Balance classes so a pile of accepts doesn't swamp the rejects
    w_pos = len(y) / (2 * max(y.sum(), 1))
    w_neg = len(y) / (2 * max(len(y) - y.sum(), 1))
    sw = np.where(y == 1, w_pos, w_neg)
    w = np.zeros(X.shape[1])
    b = 0.0
    for _ in range(steps):
        p = 1 / (1 + np.exp(-(X @ w + b)))
        g = (p - y) * sw
        w -= lr * (X.T @ g / len(y) + l2 * w)
        b -= lr * g.mean()
    return w, b


def _metrics(y: np.ndarray, pred: np.ndarray) -> dict:
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    return {"accuracy": round(float((pred == y).mean()), 3) if len(y) else None,
            "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None}


def train(detector: Detector) -> None:
    feats, ys = [], []
    for f, y in labels(detector.response):
        feats.append(f)
        ys.append(y)
    y_all = np.array(ys)
    if y_all.sum() < MIN_EACH or (len(y_all) - y_all.sum()) < MIN_EACH:
        raise ValueError(f"Needs at least {MIN_EACH} accepted and {MIN_EACH} rejected shelters "
                         f"(has {int(y_all.sum())} and {int(len(y_all) - y_all.sum())})")
    _fill_stats(feats)
    X_all = np.array([analysis.vector(f.properties["stats"]) for f in feats])
    test = np.array([_held_out(f) for f in feats])
    mean, scale = X_all[~test].mean(axis=0), X_all[~test].std(axis=0) + 1e-6
    Xs = (X_all - mean) / scale
    w, b = _fit(Xs[~test], y_all[~test])
    prob = 1 / (1 + np.exp(-(Xs @ w + b)))
    # The built-in rules on the same held-out reviews, for comparison
    base = np.array([analysis.score(f.properties["stats"]["area_m2"], f.properties["stats"]["compact"], "shelter")
                     for f in feats])
    yt = y_all[test]
    m = _metrics(yt, (prob[test] >= 0.5).astype(int))
    mb = _metrics(yt, (base[test] >= 0.5).astype(int))
    # Rules: widen towards the shelters people accepted or drew (so fewer are missed),
    # a step at a time from the previous version, never narrower than the built-in ones
    prev = analysis.latest_detector(detector.response)
    was = {**analysis.DEFAULT_RULES, **((prev.params.get("rules") if prev else None) or {})}
    pos = [f.properties["stats"] for f, yy in zip(feats, ys, strict=True) if yy]
    areas = np.array([st["area_m2"] for st in pos])
    bright = np.percentile([st["bright"] for st in pos], 5) * 255
    sat = np.percentile([st["sat"] for st in pos], 95)
    rules = {
        "grey_min": int(min(analysis.DEFAULT_RULES["grey_min"], max(was["grey_min"] - 15, bright, 90))),
        "sat_max": round(float(max(analysis.DEFAULT_RULES["sat_max"], min(was["sat_max"] + 0.04, sat, 0.25))), 3),
        "shelter_m2": [round(float(max(2, min(was["shelter_m2"][0], np.percentile(areas, 2)))), 1),
                       round(float(max(was["shelter_m2"][1], min(120, np.percentile(areas, 98)))), 1)],
    }
    detector.params = {"rules": rules, "features": list(analysis.FEATURES), "mean": mean.tolist(), "scale": scale.tolist(),
                       "weights": w.tolist(), "bias": float(b), "drop_below": 0.15}
    detector.metrics = {"examples": len(ys), "positives": int(y_all.sum()), "negatives": int(len(ys) - y_all.sum()),
                        "added": sum(1 for f in feats if f.properties.get("added")), "held_out": int(test.sum()),
                        **m, "baseline": mb}
    detector.status = "ready"
    detector.error = ""
    detector.save()


def next_version(response: Response) -> int:
    return (response.detectors.aggregate(m=Max("version"))["m"] or 0) + 1


# ---- training data export ---------------------------------------------------------


README = """# Shelter labels for training a segmentation model

From the RISA Dashboard: {site}, {layer}.
Imagery: {attribution}.

- image.tif: the area of interest, cut from the orthomosaic (EPSG:3857 COG).
- labels.geojson: shelters and buildings people accepted, corrected or drew
  (`source`: accepted | edited | added). Use these as positives.
- negatives.geojson: suggestions people rejected (false positives).
- aoi.geojson: the area that was reviewed. Unlabelled space inside it isn't
  necessarily empty: only reviewed suggestions are labelled.

This is the input HOT's fAIr / RAMP training takes (imagery plus footprint labels).
Detections came from {model}{simulated}.
"""


def training_data(layer: Layer, out_path: str) -> str:
    src = Layer.objects.get(id=layer.meta["source_layer"])
    w, s, e, n = layer.meta["aoi"]

    def fc(qs, source):
        feats = []
        for f in qs:
            p = f.properties
            src_label = "added" if p.get("added") else "edited" if p.get("edited") else source
            feats.append({"type": "Feature", "geometry": json.loads(f.geom.geojson),
                          "properties": {"class": f.risa_type, "source": src_label, "confidence": p.get("confidence"),
                                         "model": p.get("model"), **(p.get("stats") or {})}})
        return {"type": "FeatureCollection", "features": feats}

    base = layer.features.filter(risa_type__in=["shelter", "building"])
    with tempfile.TemporaryDirectory() as tmp:
        img = os.path.join(tmp, "image.tif")
        with storage.local_copy(src.source, suffix=".tif") as cog:
            run(["gdal_translate", "-q", "-of", "COG", "-co", "COMPRESS=JPEG", "-projwin_srs", "EPSG:4326",
                 "-projwin", str(w), str(n), str(e), str(s), cog, img])
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(img, "image.tif")
            z.writestr("labels.geojson", json.dumps(fc(base.filter(properties__review="accepted"), "accepted")))
            z.writestr("negatives.geojson", json.dumps(fc(base.filter(properties__review="rejected"), "rejected")))
            z.writestr("aoi.geojson", json.dumps({"type": "Feature", "properties": {}, "geometry": {
                "type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}}))
            z.writestr("README.md", README.format(
                site=layer.site.name, layer=src.name, attribution=src.attribution or "see the dashboard",
                model=layer.meta.get("model", analysis.MODEL),
                simulated=" (simulated: a stand-in for a model)" if layer.meta.get("simulated") else ""))
    return out_path

