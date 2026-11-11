"""How good is a detector? Its results on an analysis layer against a reference: shelters
a person marked (points, one click per shelter) or outlined (polygons), in another layer.

Only the area the reference covers is scored, so a reference that covers part of the
image doesn't count the rest as misses: a given box; else the reference layer's own
areas (polygons with properties.role = "area": where the person looked, which may hold
no shelters at all); else its features' outline grown by 5 m. Matching is one to one, most confident detection first:

    reference point    matched by the detection that contains it
    reference outline  matched by the detection overlapping it most, if IoU >= 0.3

Reported: precision (detections that are shelters), recall (shelters found), F1, count
error, the share of confident (>= 0.75) detections that are wrong ("wrong and unflagged",
the measure the plan cares about), and the same at each confidence threshold, so a
partner can pick the operating point. Raw model output is scored: suggestions whatever
their review, so a person's corrections don't flatter the model.
"""

from django.contrib.gis.geos import GEOSGeometry, Polygon
from django.db import connection
from django.utils import timezone

from .models import Layer

IOU = 0.3
CONFIDENT = 0.75
THRESHOLDS = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9]


def _area(reference: Layer, bbox: list[float] | None) -> GEOSGeometry:
    if bbox:
        area = Polygon.from_bbox(bbox)
        area.srid = 4326
        return area
    with connection.cursor() as cur:
        cur.execute("""SELECT ST_AsEWKT(ST_Multi(ST_Union(geom))) FROM risa_feature
                       WHERE layer_id = %s AND properties->>'role' = 'area'""", [str(reference.id)])
        ewkt = cur.fetchone()[0]
        if ewkt:
            return GEOSGeometry(ewkt)
        # The reference's outline, grown 5 m: where the person looked
        cur.execute("""
            SELECT ST_AsEWKT(ST_Transform(ST_Buffer(ST_ConvexHull(ST_Collect(ST_Transform(geom, 3857))), 5), 4326))
            FROM risa_feature WHERE layer_id = %s""", [str(reference.id)])
        ewkt = cur.fetchone()[0]
    if not ewkt:
        raise ValueError("The reference layer has no features")
    return GEOSGeometry(ewkt)


def evaluate(layer: Layer, reference: Layer, cls: str = "shelter", bbox: list[float] | None = None,
             save: bool = True) -> dict:
    area = _area(reference, bbox)
    with connection.cursor() as cur:
        cur.execute("""
            SELECT id::text, coalesce((properties->>'confidence')::float, 0) FROM risa_feature
            WHERE layer_id = %s AND coalesce(properties->>'ai_class', risa_type) = %s
              AND ST_Intersects(ST_PointOnSurface(geom), ST_GeomFromEWKT(%s))""", [str(layer.id), cls, area.ewkt])
        dets = dict(cur.fetchall())
        cur.execute("""
            SELECT id::text, GeometryType(geom) LIKE '%%POINT' FROM risa_feature
            WHERE layer_id = %s AND (risa_type IN (%s, '') OR risa_type IS NULL)
              AND coalesce(properties->>'role', '') <> 'area'
              AND ST_Intersects(geom, ST_GeomFromEWKT(%s))""", [str(reference.id), cls, area.ewkt])
        refs = dict(cur.fetchall())
        # Candidate pairs and their overlap: 1 for a point inside, IoU for an outline
        cur.execute("""
            SELECT d.id::text, r.id::text,
                   CASE WHEN GeometryType(r.geom) LIKE '%%POINT' THEN 1.0
                        ELSE ST_Area(ST_Intersection(d.geom, r.geom)::geography)
                             / NULLIF(ST_Area(ST_Union(d.geom, r.geom)::geography), 0) END
            FROM risa_feature d JOIN risa_feature r ON r.layer_id = %s AND ST_Intersects(d.geom, r.geom)
            WHERE d.layer_id = %s AND d.id::text = ANY(%s) AND r.id::text = ANY(%s)""",
                    [str(reference.id), str(layer.id), list(dets), list(refs)])
        pairs = [(d, r, float(o or 0)) for d, r, o in cur.fetchall()]

    by_det: dict[str, list[tuple[str, float]]] = {}
    for d, r, o in pairs:
        if refs[r] or o >= IOU:
            by_det.setdefault(d, []).append((r, o))

    def score(min_conf: float) -> dict:
        taken, tp, fp_confident, n_confident = set(), 0, 0, 0
        chosen = sorted((d for d, c in dets.items() if c >= min_conf), key=lambda d: -dets[d])
        for d in chosen:
            best = max(((r, o) for r, o in by_det.get(d, []) if r not in taken), key=lambda x: x[1], default=None)
            if best:
                taken.add(best[0])
                tp += 1
            if dets[d] >= CONFIDENT:
                n_confident += 1
                fp_confident += 0 if best else 1
        n, m = len(chosen), len(refs)
        p = tp / n if n else 0.0
        rc = tp / m if m else 0.0
        return {"min_confidence": min_conf, "detected": n, "matched": tp, "precision": round(p, 3),
                "recall": round(rc, 3), "f1": round(2 * p * rc / (p + rc), 3) if p + rc else 0.0,
                "count_error": round((n - m) / m, 3) if m else 0.0,
                "wrong_confident": round(fp_confident / n_confident, 3) if n_confident else 0.0}

    curve = [score(t) for t in THRESHOLDS]
    best = max(curve, key=lambda x: x["f1"])
    with connection.cursor() as cur:
        cur.execute("SELECT ST_Area(ST_GeomFromEWKT(%s)::geography)", [area.ewkt])
        area_m2 = cur.fetchone()[0]
    result = {
        **curve[0], "reference": str(reference.id), "reference_name": reference.name,
        "reference_count": len(refs), "reference_kind": "points" if refs and all(refs.values()) else "outlines",
        "class": cls, "area_m2": round(area_m2), "best_threshold": best["min_confidence"], "best_f1": best["f1"],
        "curve": curve, "model": layer.meta.get("model"), "simulated": layer.meta.get("simulated", True),
        "at": timezone.now().isoformat(),
    }
    if save:
        layer.meta = {**layer.meta, "evaluation": result}
        layer.save(update_fields=["meta", "updated_at"])
    return result
