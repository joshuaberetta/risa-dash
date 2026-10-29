"""Figures for the site panel and the at-a-glance block on page 1."""

from collections import defaultdict

from .geofuncs import GeometryType
from .models import Feature, Site
from .symbology import symbology

EMPTY = {"ok": 0, "partial": 0, "no": 0, "unknown": 0}


def site_summary(site: Site, layer_ids: list[str] | None = None) -> dict:
    qs = Feature.objects.filter(layer__site=site, layer__status="ready")
    if layer_ids is not None:
        qs = qs.filter(layer_id__in=layer_ids)
    qs = qs.annotate(gt=GeometryType("geom"))
    by_type: dict[str, dict] = defaultdict(lambda: dict(EMPTY))
    routes = dict(EMPTY)
    route_list = []
    shelters = 0
    pending = 0
    for f in qs.only("risa_type", "risa_status", "label", "properties").iterator():
        review = f.properties.get("review")
        if review is not None and review != "accepted":
            # Imagery-analysis suggestions count only once a person accepts them
            pending += review == "suggested"
            continue
        if f.risa_type in ("block", "boundary", "building"):
            continue
        st = f.risa_status or "unknown"
        is_line = "LINE" in (f.gt or "").upper()
        if f.risa_type == "route" or (is_line and not f.risa_type):
            routes[st] += 1
            route_list.append({"label": f.label, "status": st, "note": str(f.properties.get("note", ""))[:200]})
        elif f.risa_type == "shelter":
            shelters += 1
        elif f.risa_type:
            by_type[f.risa_type][st] += 1
    types = symbology()["types"]
    services = [
        {"type": t, "label": types.get(t, {}).get("label", t), **c, "total": sum(c.values())}
        for t, c in sorted(by_type.items(), key=lambda kv: -sum(kv[1].values()))
        if t not in ("block", "flood", "debris", "gate", "choke")
    ]
    water = by_type.get("water", dict(EMPTY))
    w_total = sum(water.values())
    r_total = sum(routes.values())
    glance = [
        {"value": "", "label": "people (estimate)", "tbc": True},
        {"value": f"{shelters:,}" if shelters else "", "label": "shelters counted on imagery", "tbc": False},
        {"value": f"{water['ok']} of {w_total}" if w_total else "", "label": "water points working", "tbc": False},
        {"value": f"{routes['ok']} of {r_total}" if r_total else "", "label": "access routes open", "tbc": False},
    ]
    return {"services": services, "routes": routes, "route_list": route_list[:20], "shelters": shelters,
            "glance": glance, "features": qs.count(), "pending_review": pending}
