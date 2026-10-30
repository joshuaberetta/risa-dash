"""
RISA page 1 (Common Operational Picture) as data for the Typst template.

The layout sizes live here and nowhere else: the Typst template places the map
image in the frame computed by `frames()`, and the worker renders the map image at
exactly that size, so the two always line up.
"""

import json
import math
from collections import OrderedDict
from xml.sax.saxutils import escape

import qrcode
import qrcode.image.svg
from django.conf import settings

from .geofuncs import GeometryType
from .models import Feature, Layer, Product
from .symbology import symbology

# Page sizes and the fixed parts of the layout, in mm
LAYOUT = {
    "A3": {"w": 420, "h": 297, "band": 24, "foot": 15, "side": 84, "base": 9.5, "inset": (54, 40), "overview": (40, 30)},
    "A4": {"w": 297, "h": 210, "band": 18, "foot": 12, "side": 66, "base": 7.2, "inset": (40, 30), "overview": (30, 22.5)},
}
INSET_OFFSET = 4  # mm from the map frame's top left
SIDE_PAD = (4.5, 4)  # the side panel's inner margin (x, y), as in page1.typ
LOCATOR_GAP = 7  # mm between the area locator and the overview, room for the leader lines

# Locator maps: the area round the site (on by default, as before) and an optional
# country overview with the area marked, as on MapAction's maps. On the map's top left
# corner, or at the top of the side panel.
DEFAULT_LOCATORS = {"area": True, "country": False, "place": "map"}

LABELS = {
    "en": {"key_message": "Key message", "at_a_glance": "At a glance", "routes": "Access routes", "services": "Services",
           "areas": "Areas", "imagery": "Imagery", "sources": "Sources", "produced_with": "Produced with the",
           "method": "method", "support": "Technical support", "scan": "Scan for the live map", "tbc": "TBC",
           "feedback": "Scan to give feedback",
           "scale_note": "at print size", "page": "Page 1", "no_features": "No mapped features yet",
           "status": {"ok": "Working", "partial": "Partly", "no": "Not working", "unknown": "Not assessed"},
           "route_status": {"ok": "Open", "partial": "Restricted", "no": "Closed", "unknown": "Not assessed"},
           "draft": "DRAFT PREVIEW", "analysis": "Imagery analysis", "simulated": "simulated", "dashed": "Dashed: not yet reviewed"},
    "es": {"key_message": "Mensaje clave", "at_a_glance": "En resumen", "routes": "Rutas de acceso", "services": "Servicios",
           "areas": "Áreas", "imagery": "Imágenes", "sources": "Fuentes", "produced_with": "Elaborado con el",
           "method": "método", "support": "Apoyo técnico", "scan": "Escanee para ver el mapa en vivo", "tbc": "POR CONF.",
           "feedback": "Escanee para opinar",
           "scale_note": "a tamaño de impresión", "page": "Página 1", "no_features": "Aún sin elementos cartografiados",
           "status": {"ok": "Funciona", "partial": "Parcialmente", "no": "No funciona", "unknown": "No evaluado"},
           "route_status": {"ok": "Abierta", "partial": "Restringida", "no": "Cerrada", "unknown": "No evaluada"},
           "draft": "BORRADOR", "analysis": "Análisis de imágenes", "simulated": "simulado", "dashed": "Discontinuo: sin revisar"},
    "fr": {"key_message": "Message clé", "at_a_glance": "En bref", "routes": "Voies d'accès", "services": "Services",
           "areas": "Zones", "imagery": "Imagerie", "sources": "Sources", "produced_with": "Réalisé avec la",
           "method": "méthode", "support": "Appui technique", "scan": "Scannez pour la carte en direct", "tbc": "À CONF.",
           "feedback": "Scannez pour donner votre avis",
           "scale_note": "à la taille d'impression", "page": "Page 1", "no_features": "Aucun élément cartographié",
           "status": {"ok": "Fonctionne", "partial": "Partiellement", "no": "Ne fonctionne pas", "unknown": "Non évalué"},
           "route_status": {"ok": "Ouverte", "partial": "Restreinte", "no": "Fermée", "unknown": "Non évaluée"},
           "draft": "BROUILLON", "analysis": "Analyse d'imagerie", "simulated": "simulée", "dashed": "Tirets : non vérifié"},
}
LABELS["pt"] = {**LABELS["en"]}

COLORS = {"band": "#1D2A3A", "band_ink": "#FFFFFF", "accent": "#E2E7EE", "accent_ink": "#1D2A3A",
          "rule": "#D9DEE4", "muted": "#4A5A6D"}

STATUS_ORDER = ["ok", "partial", "no", "unknown"]
ANALYSIS_LABELS = {"shelter": "Shelter (detected)", "building": "Building (detected)",
                   "block": "Detected block", "boundary": "Detected site boundary"}
AREA_STYLE = {"block": ("#C8A86B73", "#8C939C"), "other": ("#3B5B7A4D", "#8C939C")}


def locators(value: dict | None) -> dict:
    """A product's locator settings, with defaults and nothing else."""
    v = {**DEFAULT_LOCATORS, **{k: x for k, x in (value or {}).items() if k in DEFAULT_LOCATORS}}
    return {"area": bool(v["area"]), "country": bool(v["country"]), "place": "side" if v["place"] == "side" else "map"}


def _locator_frames(L: dict, loc: dict) -> dict:
    """Where each locator goes, in mm from the top left of its container: the map
    frame, or the side panel's content box. The overview sits under the area locator."""
    if loc["place"] == "side":
        cw = L["side"] - 2 * SIDE_PAD[0]
        area, over, x = (cw, round(cw * 0.62, 1)), (round(cw * 0.6, 1), round(cw * 0.45, 1)), 0
    else:
        area, over, x = L["inset"], L["overview"], INSET_OFFSET
    out = {"place": loc["place"], "area": None, "overview": None}
    y = x
    if loc["area"]:
        out["area"] = {"x": x, "y": y, "w": area[0], "h": area[1]}
        y += area[1] + LOCATOR_GAP
    if loc["country"]:
        out["overview"] = {"x": x, "y": y, "w": over[0], "h": over[1]}
        y += over[1] + LOCATOR_GAP
    w = max((f["x"] + f["w"] for f in (out["area"], out["overview"]) if f), default=0)
    out["size"] = [w, max(0, y - LOCATOR_GAP)]
    return out


def frames(page_size: str, locator_settings: dict | None = None) -> dict:
    """The map frame and the locator maps, in mm, for a page size."""
    L = LAYOUT.get(page_size, LAYOUT["A3"])
    map_w, map_h = L["w"] - L["side"], L["h"] - L["band"] - L["foot"]
    return {"page": L, "map": (map_w, map_h), "inset": L["inset"],
            "locators": _locator_frames(L, locators(locator_settings))}


# ---- symbols as SVG (same drawing as frontend/src/map/symbols.ts) -------------------


def symbol_svg(type_: str, status: str) -> str:
    sym = symbology()
    st = sym["status"].get(status) or sym["status"]["unknown"]
    glyph = escape((sym["types"].get(type_) or sym["types"]["other"])["glyph"])
    ink, c = sym["ink"], st["color"]
    R = 11
    circle = f'<circle cx="13" cy="13" r="{R}"'
    text = lambda fill: (f'<text x="13" y="17.4" text-anchor="middle" font-family="Inter" font-weight="700" '  # noqa: E731
                         f'font-size="12.5" fill="{fill}">{glyph}</text>') if glyph else ""
    if status == "ok":
        body = f'{circle} fill="{c}" stroke="#fff" stroke-width="2"/>{text("#fff")}'
    elif status == "partial":
        body = (f'{circle} fill="#fff"/><path d="M2 13 A11 11 0 0 0 24 13 Z" fill="{c}"/>'
                f'{circle} fill="none" stroke="{c}" stroke-width="3"/>{text(ink)}')
    elif status == "no":
        d = R * 0.72
        body = (f'{circle} fill="#fff" stroke="{c}" stroke-width="3"/>{text(c)}'
                f'<path d="M{13 - d} {13 + d} L{13 + d} {13 - d}" stroke="{c}" stroke-width="3"/>')
    else:
        body = f'{circle} fill="#fff" stroke="{c}" stroke-width="2.4"/>{text(c)}'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 26 26" width="26" height="26">{body}</svg>'


def qr_svg(url: str) -> str:
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=0,
                      error_correction=qrcode.constants.ERROR_CORRECT_M)
    return img.to_string(encoding="unicode")


# ---- data -------------------------------------------------------------------------


def visible_layers(product: Product, view: dict) -> list[Layer]:
    order = list(product.site.layers.filter(status="ready").order_by("-z_order", "created_at"))
    vl = {x["id"]: x for x in view.get("layers", [])}
    if not vl:
        return [lyr for lyr in order if lyr.visible_default]
    return [lyr for lyr in order if vl.get(str(lyr.id), {}).get("visible", False)]


def legend(layers: list[Layer]) -> dict:
    routes, statuses = set(), set()
    services, areas = OrderedDict(), OrderedDict()
    analysis_layers = [lyr for lyr in layers if lyr.kind == "analysis"]
    a_rows = (Feature.objects.filter(layer__in=analysis_layers).exclude(properties__review="rejected")
              .values_list("risa_type", "properties__review").distinct())
    a_classes = {t for t, _ in a_rows}
    a_suggested = any(r in (None, "suggested") for _, r in a_rows)
    a_colors = symbology().get("analysis", {})
    rows = (Feature.objects.filter(layer__in=[lyr for lyr in layers if lyr.is_vector and lyr.kind != "analysis"])
            .annotate(gt=GeometryType("geom")).values_list("gt", "risa_type", "risa_status").distinct())
    for gt, t, st in rows:
        st = st or "unknown"
        if "LINE" in gt:
            routes.add(st)
        elif "POLYGON" in gt:
            areas[t or "other"] = True
        else:
            services[t or "other"] = True
            statuses.add(st)
    types = symbology()["types"]
    hz = symbology()["hazards"]

    def area(t):
        if t in hz:
            return {"type": t, "label": types.get(t, {}).get("label", t), "fill": _hex(hz[t]["fill"]), "stroke": hz[t]["color"]}
        fill, stroke = AREA_STYLE.get(t, AREA_STYLE["other"])
        return {"type": t, "label": types.get(t, {}).get("label", "Mapped area" if t == "other" else t), "fill": fill, "stroke": stroke}

    return {
        "routes": [s for s in STATUS_ORDER if s in routes],
        "services": sorted(({"type": t, "label": types.get(t, {}).get("label", t)} for t in services), key=lambda x: x["label"]),
        "statuses": [s for s in STATUS_ORDER if s in statuses] or (["ok", "partial", "no"] if services else []),
        "areas": sorted((area(t) for t in areas), key=lambda x: x["label"]),
        "analysis": {
            "classes": [{"type": c, "label": ANALYSIS_LABELS[c], "color": a_colors.get(c, {}).get("color", "#7048E8"),
                         "area": c in ("block", "boundary")} for c in ANALYSIS_LABELS if c in a_classes],
            "simulated": any(lyr.meta.get("simulated") for lyr in analysis_layers),
            "suggested": a_suggested,
        },
    }


def _hex(css: str) -> str:
    """'rgba(47,116,181,0.16)' -> '#2F74B529' (Typst takes 8-digit hex)."""
    if css.startswith("#"):
        return css
    parts = css[css.index("(") + 1: css.index(")")].split(",")
    r, g, b = (int(float(x)) for x in parts[:3])
    a = float(parts[3]) if len(parts) > 3 else 1
    return f"#{r:02X}{g:02X}{b:02X}{round(a * 255):02X}"


def sources(product: Product, layers: list[Layer], basemap_attribution: str) -> str:
    if product.sources.strip():
        return product.sources.strip()
    parts = []
    for lyr in layers:
        bits = [lyr.attribution or lyr.name]
        if lyr.resolution_cm:
            bits.append(f"{lyr.resolution_cm:g} cm/px")
        if lyr.captured_at:
            bits.append(lyr.captured_at.strftime("%d/%m/%Y"))
        if lyr.kind == "kobo" and hasattr(lyr, "kobo"):
            bits.append(f"{lyr.kobo.submission_count} points")
        parts.append(", ".join(bits))
    if basemap_attribution:
        parts.append(f"Base: {basemap_attribution}")
    return ". ".join(parts) + "."


def scale_bar(m_per_mm: float, max_mm: float = 40) -> dict:
    raw = m_per_mm * max_mm
    p = 10 ** math.floor(math.log10(raw))
    nice = next(n * p for n in (5, 2, 1) if n * p <= raw)
    label = f"{nice / 1000:g} km" if nice >= 1000 else f"{nice:g} m"
    return {"mm": round(nice / m_per_mm, 2), "label": label, "ratio": f"1:{round(m_per_mm * 1000):,}"}


def build(product: Product, snapshot: dict, map_state: dict, when, draft: bool, basemap_attribution: str,
          version_n: int | None = None) -> dict:
    """Everything the template reads, as JSON. `map_state` comes from the map render:
    {zoom, lat, bearing, m_per_px} in CSS px of the frame, and `marker`: where the
    area locator's extent is on the overview, as fractions [x0, y0, x1, y1]."""
    p = {**snapshot.get("product", {})}
    view = p.get("view") or product.view
    f = frames(p.get("page_size") or product.page_size, p.get("locators") or product.locators)
    layers = visible_layers(product, view)
    summary = snapshot.get("summary") or {}
    glance = []
    for i, g in enumerate(summary.get("glance", [])):
        o = (p.get("glance") or [])[i] if i < len(p.get("glance") or []) else None
        glance.append({"value": (o or {}).get("value") or g["value"], "label": (o or {}).get("label") or g["label"],
                       "tbc": (o or g).get("tbc", False)})
    site = product.site
    lang = site.response.language if site.response.language in LABELS else "en"
    m_per_mm = map_state["m_per_px"] * 96 / 25.4
    url = f"{settings.PUBLIC_URL}/r/{site.response.slug}/{site.slug}"
    # The feedback QR code is printed small, and a form link with its prefilled values
    # runs to 300+ characters: too dense to scan. So it points here, and /f/ redirects
    # to the form with the values filled in (views.feedback).
    feedback = ""
    if site.response.feedback_link(site, product):
        feedback = f"{settings.PUBLIC_URL}/f/{product.id}" + (f"/{version_n}" if version_n else "")
    return {
        "page": {**f["page"], "inset": list(f["inset"]), "overview": list(f["page"]["overview"]), "map": list(f["map"]),
                 "side_pad": list(SIDE_PAD), "locators": f["locators"]},
        "lang": lang,
        "labels": LABELS[lang],
        "colors": {**COLORS, "ink": symbology()["ink"], "status": {k: v["color"] for k, v in symbology()["status"].items()}},
        "draft": draft,
        "title": p.get("title") or product.title,
        "subtitle": " · ".join(x for x in (site.name, site.place, site.response.name) if x),
        "code": " · ".join(x for x in (p.get("code") or product.code, p.get("version_label") or product.version_label) if x),
        "date": when.strftime("%d/%m/%Y %H:%M"),
        "glide": site.response.glide,
        "authority": p.get("authority") or product.authority,
        "key_message": p.get("key_message") or product.key_message,
        "glance": glance,
        "legend": legend(layers),
        "sources": sources(product, layers, basemap_attribution),
        "disclaimer": p.get("disclaimer") or product.disclaimer,
        "credits": p.get("credits") or product.credits,
        "url": url,
        "feedback": feedback,
        "bearing": map_state.get("bearing", 0),
        "marker": map_state.get("marker"),
        "scale": scale_bar(m_per_mm),
    }


def write_assets(root, data: dict) -> None:
    """data.json, qr.svg (and feedback.svg) and one SVG per legend symbol, next to the template."""
    (root / "data.json").write_text(json.dumps(data, ensure_ascii=False))
    (root / "qr.svg").write_text(qr_svg(data["url"]))
    if data.get("feedback"):
        (root / "feedback.svg").write_text(qr_svg(data["feedback"]))
    sym_dir = root / "sym"
    sym_dir.mkdir(exist_ok=True)
    for s in data["legend"]["services"]:
        (sym_dir / f"{s['type']}-ok.svg").write_text(symbol_svg(s["type"], "ok"))
    for st in STATUS_ORDER:
        (sym_dir / f"water-{st}.svg").write_text(symbol_svg("water", st))
