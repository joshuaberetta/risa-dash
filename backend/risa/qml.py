"""QGIS styles (QML) for the GeoPackage export, so a layer opens in QGIS looking as it does
on the dashboard's map (frontend/src/map/style.ts): status shown twice, by colour and by
line style or symbol shape; point symbols are page 1's SVGs; labels from risa_label.

A rule per type and status present in the table, so QGIS's legend lists only what is on
the map, and an ELSE rule for anything else. Sizes are in millimetres, about the map's
pixels at 96 dpi.
"""

import base64
from xml.sax.saxutils import quoteattr

from .page1 import symbol_svg
from .symbology import symbology

BASE = "#3B5B7A"  # a layer's colour when its features have no status
BLOCK = "#C8A86B"
STATUSES = ("ok", "partial", "no", "unknown")


def _rgba(css: str, alpha: float = 1.0) -> str:
    css = css.lstrip("#")
    r, g, b = (int(css[i:i + 2], 16) for i in (0, 2, 4))
    return f"{r},{g},{b},{round(alpha * 255)}"


def _opts(**kw) -> str:
    return "".join(f'<Option name="{k}" type="QString" value={quoteattr(str(v))}/>' for k, v in kw.items())


def _layer(cls: str, **kw) -> str:
    return f'<layer class="{cls}" enabled="1" locked="0" pass="0"><Option type="Map">{_opts(**kw)}</Option></layer>'


def _symbol(kind: str, name: str, layers: list[str]) -> str:
    return f'<symbol type="{kind}" name="{name}" alpha="1" clip_to_extent="1" force_rhr="0">{"".join(layers)}</symbol>'


def _line(color: str, width: float, status: str) -> str:
    """A line in the status's style: solid, dashed or dotted."""
    common = dict(line_color=color, line_width=width, line_width_unit="MM", joinstyle="round")
    if status == "partial":
        return _layer("SimpleLine", **common, capstyle="flat", use_custom_dash=1,
                      customdash=f"{width * 2:g};{width}", customdash_unit="MM")
    if status == "no":
        w = round(width * 1.15, 2)
        return _layer("SimpleLine", **{**common, "line_width": w}, capstyle="round", use_custom_dash=1,
                      customdash=f"0.01;{w * 1.7:g}", customdash_unit="MM")
    return _layer("SimpleLine", **common, capstyle="round")


def _casing(width: float) -> str:
    return _layer("SimpleLine", line_color="255,255,255,255", line_width=width + 1, line_width_unit="MM",
                  joinstyle="round", capstyle="round")


def _fill(color: str) -> str:
    return _layer("SimpleFill", color=color, style="solid", outline_style="no")


def _svg_marker(type_: str, status: str) -> str:
    # Qt's SVG renderer takes one font name, not a list; Arial is everywhere or substituted
    svg = symbol_svg(type_, status).replace('font-family="Inter"', 'font-family="Arial"')
    return _layer("SvgMarker", name="base64:" + base64.b64encode(svg.encode()).decode(), size=5.5, size_unit="MM")


def _labels(field: str, placement: int, bold: bool, size: float, dist: float = 0, obstacle: bool = True,
            expression: bool = False) -> str:
    """Simple labelling on a field. Placement: 1 over the centroid, 3 curved along a line, 6 at
    set positions round a point (below it first, as on the map). obstacle: other labels avoid
    this layer's features."""
    return (
        '<labeling type="simple"><settings calloutType="simple">'
        f'<text-style fieldName={quoteattr(field)} isExpression="{int(expression)}" fontSize="{size}" fontSizeUnit="Point" '
        f'fontWeight="{75 if bold else 50}" forcedBold="{int(bold)}" textColor="{_rgba(symbology()["ink"])}" textOpacity="1">'
        '<text-buffer bufferDraw="1" bufferSize="0.7" bufferSizeUnits="MM" bufferColor="255,255,255,230" bufferOpacity="1"/>'
        '</text-style>'
        f'<placement placement="{placement}" dist="{dist}" distUnits="MM" placementFlags="10" overrunDistance="0" '
        'predefinedPositionOrder="B,BR,BL,R,L,T,TR,TL"/>'
        f'<rendering obstacle="{int(obstacle)}" scaleVisibility="0" fontLimitPixelSize="0" drawLabels="1" upsidedownLabels="0"/>'
        '</settings></labeling>'
    )


def _qml(geometry: int, rules: list[tuple[str, str, str]], symbols: list[str], labeling: str, opacity: float) -> str:
    """rules: (filter, label, symbol name). geometry: 0 point, 1 line, 2 polygon."""
    rule_xml = "".join(f'<rule key="r{i}" filter={quoteattr(f)} label={quoteattr(lbl)} symbol="{s}"/>'
                       for i, (f, lbl, s) in enumerate(rules))
    return (
        "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>"
        '<qgis version="3.40.0" styleCategories="Symbology|Labeling|Rendering" labelsEnabled="1">'
        f'<renderer-v2 type="RuleRenderer" symbollevels="0" enableorderby="0" forceraster="0">'
        f'<rules key="root">{rule_xml}</rules><symbols>{"".join(symbols)}</symbols></renderer-v2>'
        f"{labeling}<layerOpacity>{opacity:g}</layerOpacity><layerGeometryType>{geometry}</layerGeometryType></qgis>"
    )


def _is(field: str, value: str) -> str:
    # Blank and missing are the same
    return f"coalesce(\"{field}\", '') = '{value}'"


def _status_is(status: str) -> str:
    return "coalesce(\"risa_status\", '') IN ('unknown', '')" if status == "unknown" else _is("risa_status", status)


def _name(type_: str, status: str) -> str:
    sym = symbology()
    t = (sym["types"].get(type_) or sym["hazards"].get(type_) or {}).get("label") or type_ or "Other"
    return f"{t} · {sym['status'][status]['short']}" if status else t


def layer_qml(geometry: str, combos: set[tuple[str, str]], style: dict, analysis: bool = False) -> str:
    """The QML for one table. geometry: points, lines or polygons; combos: the (risa_type,
    risa_status) pairs in it; style: the layer's style (opacity, color, label_field)."""
    if analysis and geometry == "polygons":
        return _analysis_qml({t for t, _ in combos}, style)
    sym = symbology()
    S, H = sym["status"], sym["hazards"]
    base = style.get("color") or BASE
    label = style.get("label_field") or "risa_label"
    opacity = float(style.get("opacity", 1))
    # Missing status reads as Not assessed for points, as the layer's colour for lines and areas
    combos = {(t, s if s in STATUSES else "") for t, s in combos}
    rules, symbols = [], []

    def add(filt: str, name: str, layers: list[str], kind: str):
        n = str(len(symbols))
        symbols.append(_symbol(kind, n, layers))
        rules.append((filt, name, n))

    if geometry == "points":
        for t, s in sorted({(t, s or "unknown") for t, s in combos}):
            glyph_type = t if t in sym["types"] else "other"
            filt = f"{_is('risa_type', t)} AND {_status_is(s)}"
            add(filt, _name(t, s), [_svg_marker(glyph_type, s)], "marker")
        add("ELSE", "Other", [_svg_marker("other", "unknown")], "marker")
        return _qml(0, rules, symbols, _labels(label, 6, False, 8, dist=0.6), opacity)

    def color(t: str, s: str) -> str:
        if t in H:
            return H[t]["color"]
        return S[s]["color"] if s else base

    if geometry == "lines":
        for t, s in sorted(combos):
            c = _rgba(color(t, s))
            layers = ([] if t in H else [_casing(1.0)]) + [_line(c, 1.0, s)]
            add(f"{_is('risa_type', t)} AND {_status_is(s) if s else _is('risa_status', '')}", _name(t, s), layers, "line")
        add("ELSE", "Other", [_casing(1.0), _line(_rgba(base), 1.0, "")], "line")
        return _qml(1, rules, symbols, _labels(label, 3, True, 8.5), opacity)

    for t, s in sorted(combos):
        fill = H[t]["color"] if t in H else BLOCK if t == "block" else (S[s]["color"] if s in ("ok", "partial", "no") else base)
        alpha = {"flood": 0.3, "debris": 0.35}.get(t, 0.45)
        outline = color(t, s)
        layers = [_fill(_rgba(fill, alpha))] + ([] if t in H or t == "block" else [_casing(0.5)]) + [_line(_rgba(outline), 0.5, s)]
        add(f"{_is('risa_type', t)} AND {_status_is(s) if s else _is('risa_status', '')}", _name(t, s), layers, "fill")
    add("ELSE", "Other", [_fill(_rgba(base, 0.45)), _line(_rgba(base), 0.5, "")], "fill")
    return _qml(2, rules, symbols, _labels(label, 1, True, 9), opacity)


def _analysis_qml(classes: set[str], style: dict) -> str:
    """Imagery analysis: colour by class, dashed while suggested, solid once accepted,
    rejected not drawn. Shelters and buildings filled, blocks and the boundary outlined."""
    A = symbology().get("analysis", {})
    review = "coalesce(\"review\", 'suggested')"
    rules, symbols = [], []
    for cls in sorted(classes or {"shelter"}):
        c = (A.get(cls) or {}).get("color") or A.get("shelter", {}).get("color", "#7048E8")
        area = cls in ("block", "boundary")
        for state, dashed, alpha in (("suggested", True, 0.18), ("accepted", False, 0.38)):
            w = (0.75 if dashed else 0.85) if area else (0.35 if dashed else 0.45)
            line = _layer("SimpleLine", line_color=_rgba(c), line_width=w, line_width_unit="MM", joinstyle="round",
                          **({"use_custom_dash": 1, "customdash": f"{w * 2:g};{w * 1.5:g}", "customdash_unit": "MM"}
                             if dashed else {}))
            layers = ([] if area else [_fill(_rgba(c, alpha))]) + [line]
            n = str(len(symbols))
            symbols.append(_symbol("fill", n, layers))
            label = (A.get(cls) or {}).get("label") or cls.capitalize()
            rules.append((f"coalesce(\"ai_class\", \"risa_type\", '') = '{cls}' AND {review} = '{state}'",
                          f"{label} · {state}", n))
    # Thousands of shelters: other layers' labels mustn't have to avoid them
    blocks = "CASE WHEN coalesce(\"ai_class\", \"risa_type\") = 'block' THEN \"risa_label\" END"
    labeling = _labels(blocks, 1, True, 9, obstacle=False, expression=True) if "block" in classes else ""
    return _qml(2, rules, symbols, labeling, float(style.get("opacity", 1)))
