"""
RISA page 2 (key findings) as data for the Typst template, one column per question:

    1. Can we reach people?     access routes and their status; logistics conditions
    2. Which services still work?  the services table; shelters by block; people (estimate)
    3. Where do we act first?   ranked gaps, each with who acts

The routes, services and logistics come from the map. Shelters by block count accepted
shelters (or drawn ones) inside the blocks the team drew, else inside detected blocks.
The gaps are the team's (Product.findings), starting from suggest_gaps(): closed and
restricted routes, services not working, hazard areas over shelters.
"""

import re

from django.db import connection

from .models import Feature, Layer, Product, Site
from .symbology import symbology

LOGISTICS = ("storage", "landing", "gate", "choke")
# Not services: flooded and debris areas, and hazards observed in the field
HAZARDS = ("flood", "debris", "hazard")
HAZARD_NEAR = 25  # metres from a hazard point
VECTOR = ("vector", "kobo", "annotations")

LABELS = {
    "en": {"page": "Page 2", "title": "Key findings", "q1": "Can we reach people?", "q2": "Which services still work?",
           "q3": "Where do we act first?", "routes_open": "{ok} of {all} access routes open", "logistics": "Logistics conditions",
           "service": "Service", "total": "Total", "working": "Working", "partly": "Partly", "not": "Not",
           "by_block": "Shelters by block", "on_imagery": "counted on imagery", "people": "people", "households": "households",
           "estimate": "Estimate", "no_routes": "No access routes mapped yet", "no_services": "No services mapped yet",
           "no_blocks": "No blocks with counted shelters yet", "no_gaps": "No gaps listed yet",
           "urgent": "Urgent", "high": "High", "per_household": "{n:g} people per shelter"},
    "es": {"page": "Página 2", "title": "Hallazgos clave", "q1": "¿Podemos llegar a la gente?", "q2": "¿Qué servicios funcionan?",
           "q3": "¿Dónde actuamos primero?", "routes_open": "{ok} de {all} rutas de acceso abiertas", "logistics": "Condiciones logísticas",
           "service": "Servicio", "total": "Total", "working": "Funciona", "partly": "Parcial", "not": "No",
           "by_block": "Refugios por bloque", "on_imagery": "contados en imágenes", "people": "personas", "households": "hogares",
           "estimate": "Estimación", "no_routes": "Aún sin rutas cartografiadas", "no_services": "Aún sin servicios cartografiados",
           "no_blocks": "Aún sin bloques con refugios contados", "no_gaps": "Aún sin brechas",
           "urgent": "Urgente", "high": "Alta", "per_household": "{n:g} personas por refugio"},
    "fr": {"page": "Page 2", "title": "Constats clés", "q1": "Pouvons-nous atteindre les gens ?", "q2": "Quels services fonctionnent ?",
           "q3": "Où agir d'abord ?", "routes_open": "{ok} voies d'accès ouvertes sur {all}", "logistics": "Conditions logistiques",
           "service": "Service", "total": "Total", "working": "Fonctionne", "partly": "Partiel", "not": "Non",
           "by_block": "Abris par bloc", "on_imagery": "comptés sur l'imagerie", "people": "personnes", "households": "ménages",
           "estimate": "Estimation", "no_routes": "Aucune voie d'accès cartographiée", "no_services": "Aucun service cartographié",
           "no_blocks": "Aucun bloc avec des abris comptés", "no_gaps": "Aucun manque listé",
           "urgent": "Urgent", "high": "Élevée", "per_household": "{n:g} personnes par abri"},
}
LABELS["pt"] = {**LABELS["en"]}

# Who acts on a gap, by RISA type: the cluster or area of responsibility. Markets go to food
# security, which leads on markets and cash in most responses (CCCM where it doesn't)
WHO = {
    "en": {"water": "WASH cluster", "latrine": "WASH cluster", "hand": "WASH cluster", "health": "Health cluster",
           "cfs": "Child protection", "dist": "Site management · CCCM", "registration": "Site management · CCCM",
           "kitchen": "Food security cluster", "storage": "Logistics cluster", "shelter": "Shelter cluster",
           "route": "Logistics cluster", "flood": "Site management · CCCM", "debris": "Site management · CCCM",
           "bathing": "WASH cluster", "waste": "WASH cluster", "safe_space": "Protection (GBV AoR)",
           "lighting": "Site management · CCCM", "energy": "Site management · CCCM", "hazard": "Site management · CCCM",
           "market": "Food security cluster", "other": "Site management · CCCM"},
    "es": {"water": "Clúster WASH", "latrine": "Clúster WASH", "hand": "Clúster WASH", "health": "Clúster de salud",
           "cfs": "Protección de la infancia", "dist": "Gestión de sitio · CCCM", "registration": "Gestión de sitio · CCCM",
           "kitchen": "Clúster de seguridad alimentaria", "storage": "Clúster de logística", "shelter": "Clúster de alojamiento",
           "route": "Clúster de logística", "flood": "Gestión de sitio · CCCM", "debris": "Gestión de sitio · CCCM",
           "bathing": "Clúster WASH", "waste": "Clúster WASH", "safe_space": "Protección (AoR VBG)",
           "lighting": "Gestión de sitio · CCCM", "energy": "Gestión de sitio · CCCM", "hazard": "Gestión de sitio · CCCM",
           "market": "Clúster de seguridad alimentaria", "other": "Gestión de sitio · CCCM"},
    "fr": {"water": "Cluster WASH", "latrine": "Cluster WASH", "hand": "Cluster WASH", "health": "Cluster santé",
           "cfs": "Protection de l'enfance", "dist": "Gestion de site · CCCM", "registration": "Gestion de site · CCCM",
           "kitchen": "Cluster sécurité alimentaire", "storage": "Cluster logistique", "shelter": "Cluster abris",
           "route": "Cluster logistique", "flood": "Gestion de site · CCCM", "debris": "Gestion de site · CCCM",
           "bathing": "Cluster WASH", "waste": "Cluster WASH", "safe_space": "Protection (AoR VBG)",
           "lighting": "Gestion de site · CCCM", "energy": "Gestion de site · CCCM", "hazard": "Gestion de site · CCCM",
           "market": "Cluster sécurité alimentaire", "other": "Gestion de site · CCCM"},
}
GAP_TEXT = {
    "en": {"route_closed": "Access: {label} closed", "routes_partial": "Access restricted on {labels}",
           "route_default": "Find another route in, or clear it.", "partial_default": "Check the conditions before sending trucks.",
           "service_no": "{type}: {no} of {total} not working", "service_partial": "{type}: {n} of {total} only partly working",
           "service_text": "{labels}: repair, or provide an alternative until then.",
           "hazard": "{hazard} over {n} shelters", "hazard_near": "{hazard} near {n} shelters", "hazard_blocks": "{hazard} reaches {blocks}: {n} shelters.",
           "hazard_text": " Plan relocation to safer ground."},
    "es": {"route_closed": "Acceso: {label} cerrada", "routes_partial": "Acceso restringido en {labels}",
           "route_default": "Buscar otra ruta o despejarla.", "partial_default": "Verificar las condiciones antes de enviar camiones.",
           "service_no": "{type}: {no} de {total} no funcionan", "service_partial": "{type}: {n} de {total} funcionan parcialmente",
           "service_text": "{labels}: reparar o dar una alternativa mientras tanto.",
           "hazard": "{hazard} sobre {n} refugios", "hazard_near": "{hazard} cerca de {n} refugios", "hazard_blocks": "{hazard} alcanza {blocks}: {n} refugios.",
           "hazard_text": " Planificar la reubicación a un terreno más seguro."},
    "fr": {"route_closed": "Accès : {label} fermée", "routes_partial": "Accès restreint sur {labels}",
           "route_default": "Trouver une autre voie ou la dégager.", "partial_default": "Vérifier les conditions avant d'envoyer des camions.",
           "service_no": "{type} : {no} sur {total} ne fonctionnent pas", "service_partial": "{type} : {n} sur {total} partiellement",
           "service_text": "{labels} : réparer, ou prévoir une alternative en attendant.",
           "hazard": "{hazard} sur {n} abris", "hazard_near": "{hazard} près de {n} abris", "hazard_blocks": "{hazard} atteint {blocks} : {n} abris.",
           "hazard_text": " Prévoir une réinstallation sur un terrain plus sûr."},
}
for t in (WHO, GAP_TEXT):
    t["pt"] = t["en"]


def _lang(site: Site) -> str:
    return site.response.language if site.response.language in LABELS else "en"


def _layers(product: Product, view: dict) -> list[Layer]:
    ids = [lyr["id"] for lyr in view.get("layers", []) if lyr.get("visible", True)]
    qs = Layer.objects.filter(site=product.site, status="ready")
    return list(qs.filter(id__in=ids) if ids else qs)


def _counted(qs):
    """Features that count: drawn or uploaded ones, and accepted analysis suggestions."""
    return [f for f in qs if f.properties.get("review") in (None, "accepted")]


def _natural(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s or "")]


def shelters_by_block(layers: list[Layer]) -> list[dict]:
    """Accepted (or drawn) shelters inside each block: the team's blocks if they drew
    any, else the detected ones. [{label, shelters}], in label order."""
    vec = [str(lyr.id) for lyr in layers if lyr.kind in VECTOR]
    ana = [str(lyr.id) for lyr in layers if lyr.kind == "analysis"]
    all_ids = vec + ana
    if not all_ids:
        return []
    sql = """
        WITH b AS (
            SELECT id, label, geom FROM risa_feature
            WHERE layer_id::text = ANY(%s) AND risa_type = 'block'
              AND coalesce(properties->>'review', 'accepted') <> 'rejected'
        ), s AS (
            SELECT ST_PointOnSurface(geom) AS p FROM risa_feature
            WHERE layer_id::text = ANY(%s) AND risa_type = 'shelter'
              AND coalesce(properties->>'review', 'accepted') = 'accepted'
        )
        SELECT b.label, count(s.p) FROM b LEFT JOIN s ON ST_Contains(b.geom, s.p)
        GROUP BY b.id, b.label HAVING count(s.p) > 0"""
    with connection.cursor() as cur:
        rows = []
        if vec:
            cur.execute(sql, [vec, all_ids])
            rows = cur.fetchall()
        if not rows and ana:
            cur.execute(sql, [ana, all_ids])
            rows = cur.fetchall()
    # Detected blocks are labelled "Block 3 · 454 shelters": the name only
    out = [{"label": (label or "").split(" · ")[0] or "–", "shelters": n} for label, n in rows]
    return sorted(out, key=lambda b: _natural(b["label"]))


def logistics(layers: list[Layer], lang: str) -> list[dict]:
    types = symbology()["types"]
    qs = Feature.objects.filter(layer__in=[lyr for lyr in layers if lyr.kind in VECTOR], risa_type__in=LOGISTICS)
    out = []
    for f in _counted(qs.order_by("risa_type", "label")):
        out.append({"label": f.label or types.get(f.risa_type, {}).get("label", f.risa_type),
                    "kind": types.get(f.risa_type, {}).get("label", f.risa_type),
                    "status": f.risa_status or "unknown", "note": str(f.properties.get("note", ""))[:160]})
    return out[:8]


def suggest_gaps(product: Product, layer_ids: list[str] | None = None) -> list[dict]:
    """Gaps from the map, most urgent first: closed routes, services not working,
    hazards over shelters, then restricted routes and services partly working.
    [{status, title, text, who}] for the team to edit."""
    site = product.site
    lang = _lang(site)
    T, who = GAP_TEXT[lang], WHO[lang]
    types = symbology()["types"]
    hazards = symbology()["hazards"]
    layers = _layers(product, {"layers": [{"id": i} for i in layer_ids]} if layer_ids else product.view)
    vec = [lyr for lyr in layers if lyr.kind in VECTOR]
    feats = _counted(Feature.objects.filter(layer__in=vec).exclude(risa_type__in=("block", "boundary", "shelter")))
    scored: list[tuple[int, int, dict]] = []  # (urgency, size, gap)

    routes = [f for f in feats if f.risa_type == "route"]
    for f in routes:
        if f.risa_status == "no":
            scored.append((3, 1, {"status": "no", "title": T["route_closed"].format(label=f.label or "–"),
                                  "text": str(f.properties.get("note") or T["route_default"]), "who": who["route"]}))
    partial = [f.label or "–" for f in routes if f.risa_status == "partial"]
    if partial:
        scored.append((1, len(partial), {"status": "partial", "title": T["routes_partial"].format(labels=", ".join(partial)),
                                         "text": T["partial_default"], "who": who["route"]}))

    by_type: dict[str, list] = {}
    for f in feats:
        if f.risa_type and f.risa_type not in ("route", *HAZARDS, *LOGISTICS):
            by_type.setdefault(f.risa_type, []).append(f)
    for t, fs in by_type.items():
        label = types.get(t, {}).get("label", t)
        no = [f for f in fs if f.risa_status == "no"]
        part = [f for f in fs if f.risa_status == "partial"]
        if no:
            names = ", ".join(sorted((f.label for f in no if f.label), key=_natural)) or label
            scored.append((3, len(no), {"status": "no", "title": T["service_no"].format(type=label, no=len(no), total=len(fs)),
                                        "text": T["service_text"].format(labels=names), "who": who.get(t, who["other"])}))
        elif part:
            names = ", ".join(sorted((f.label for f in part if f.label), key=_natural)) or label
            scored.append((1, len(part), {"status": "partial",
                                          "title": T["service_partial"].format(type=label, n=len(part), total=len(fs)),
                                          "text": T["service_text"].format(labels=names), "who": who.get(t, who["other"])}))

    # Hazards over shelters: accepted or drawn shelters inside each flood or debris area, or
    # within HAZARD_NEAR metres of a hazard observed as a point
    ids = [str(lyr.id) for lyr in layers if lyr.kind in VECTOR or lyr.kind == "analysis"]
    if ids:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT h.risa_type, h.label,
                       (SELECT count(*) FROM risa_feature s WHERE s.layer_id::text = ANY(%s) AND s.risa_type = 'shelter'
                          AND coalesce(s.properties->>'review', 'accepted') = 'accepted'
                          AND (ST_Intersects(s.geom, h.geom) OR (h.risa_type = 'hazard'
                               AND ST_DWithin(s.geom::geography, h.geom::geography, %s)))),
                       (SELECT string_agg(DISTINCT split_part(b.label, ' · ', 1), ', ') FROM risa_feature b
                          WHERE b.layer_id::text = ANY(%s) AND b.risa_type = 'block' AND b.label <> ''
                          AND coalesce(b.properties->>'review', 'accepted') <> 'rejected' AND ST_Intersects(b.geom, h.geom))
                FROM risa_feature h WHERE h.layer_id::text = ANY(%s) AND h.risa_type = ANY(%s)""",
                        [ids, HAZARD_NEAR, [str(lyr.id) for lyr in vec], [str(lyr.id) for lyr in vec], list(HAZARDS)])
            for t, label, n, blocks in cur.fetchall():
                if not n and not blocks:
                    continue
                name = label or (hazards.get(t) or types[t])["label"]
                text = (T["hazard_blocks"].format(hazard=name, blocks=blocks, n=n) if blocks else "") + T["hazard_text"]
                title = T["hazard_near" if t == "hazard" else "hazard"].format(hazard=name, n=n)
                scored.append((2 if n else 1, n, {"status": "no" if n else "partial", "title": title, "text": text.strip(),
                                                  "who": who[t]}))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [g for _, _, g in scored[:5]]


def build(product: Product, snapshot: dict, summary: dict) -> dict:
    """What page 2 prints. `snapshot` is the product as printed (findings, view, glance)."""
    p = snapshot.get("product", {})
    site = product.site
    lang = _lang(site)
    view = p.get("view") or product.view
    layers = _layers(product, view)
    findings = p.get("findings") if "findings" in p else product.findings
    routes = summary.get("route_list", [])
    r = summary.get("routes", {})
    r_all = sum(r.values())
    verdict = "unknown" if not r_all else "ok" if r.get("ok") == r_all else "no" if not r.get("ok") else "partial"
    blocks = shelters_by_block(layers)
    shelters = summary.get("shelters", 0)
    size = float(site.response.household_size or 5)
    glance = p.get("glance") or product.glance or []
    people_override = (glance[0].get("value") if glance else "") or ""
    return {
        "labels": LABELS[lang],
        "routes": routes[:8],
        "routes_open": LABELS[lang]["routes_open"].format(ok=r.get("ok", 0), all=r_all) if r_all else "",
        "verdict": verdict,
        "reach_note": (findings or {}).get("reach_note", ""),
        "logistics": logistics(layers, lang),
        # Storage, landing zones, gates and choke points are logistics, in column 1
        "services": [{k: s[k] for k in ("type", "label", "total", "ok", "partial", "no")}
                     for s in summary.get("services", []) if s["type"] not in LOGISTICS][:10],
        "blocks": blocks[:16],
        "block_max": max([b["shelters"] for b in blocks] or [1]),
        "people": people_override or (f"{round(shelters * size):,}" if shelters else ""),
        "households": f"{shelters:,}" if shelters else "",
        "household_note": LABELS[lang]["per_household"].format(n=size),
        "gaps": [g for g in (findings or {}).get("gaps", []) if g.get("title")][:5],
    }
