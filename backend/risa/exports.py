"""GIS exports: a GeoPackage with one table per vector layer, each with its QGIS style,
and GeoJSON."""

import json
import os
import re
import sqlite3
import subprocess
import tempfile

from django.contrib.gis.db.models.functions import AsGeoJSON

from . import qml
from .geofuncs import GeometryType
from .models import Layer, Site


def layer_geojson(layer: Layer, flat: bool = False) -> dict:
    feats = []
    qs = layer.features.annotate(gj=AsGeoJSON("geom", precision=7)).values(
        "id", "gj", "properties", "risa_type", "risa_status", "label", "observed_at"
    )
    for f in qs.iterator(chunk_size=2000):
        props = dict(f["properties"] or {})
        if flat:
            props = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict | list) else v) for k, v in props.items()}
        props.update({
            "risa_id": str(f["id"]), "risa_type": f["risa_type"], "risa_status": f["risa_status"],
            "risa_label": f["label"], "observed_at": f["observed_at"].isoformat() if f["observed_at"] else None,
        })
        feats.append({"type": "Feature", "id": str(f["id"]), "geometry": json.loads(f["gj"]), "properties": props})
    return {"type": "FeatureCollection", "features": feats}


GEOM_GROUPS = [
    ("points", "OGR_GEOMETRY IN ('POINT','MULTIPOINT')", "POINT", "MULTIPOINT"),
    ("lines", "OGR_GEOMETRY IN ('LINESTRING','MULTILINESTRING')", "LINESTRING", "MULTILINESTRING"),
    ("polygons", "OGR_GEOMETRY IN ('POLYGON','MULTIPOLYGON')", "POLYGON", "MULTIPOLYGON"),
]
GEOM_TYPES = {"points": ("POINT", "MULTIPOINT"), "lines": ("LINESTRING", "MULTILINESTRING"),
              "polygons": ("POLYGON", "MULTIPOLYGON")}


def _table_name(name: str, used: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:50] or "layer"
    n, i = base, 2
    while n in used:
        n, i = f"{base}_{i}", i + 1
    used.add(n)
    return n


def site_geopackage(site: Site, out_path: str) -> str:
    used: set[str] = set()
    styles: list[tuple[str, str, str]] = []  # (table, layer name, QML)
    with tempfile.TemporaryDirectory() as tmp:
        for layer in site.layers.filter(kind__in=["vector", "kobo", "annotations", "analysis"], status="ready"):
            if not layer.features.exists():
                continue
            src = os.path.join(tmp, f"{layer.id}.geojson")
            with open(src, "w") as f:
                json.dump(layer_geojson(layer, flat=True), f, ensure_ascii=False)
            present = {g.replace("MULTI", "") for g in
                       layer.features.annotate(t=GeometryType("geom")).values_list("t", flat=True).distinct()}
            # Mixed geometry types: one table per type, suffixed only when a layer has several
            groups = [(n, w, nlt) for n, w, key, nlt in GEOM_GROUPS if key in present]
            for gtype, where, nlt in groups:
                table = _table_name(layer.name if len(groups) == 1 else f"{layer.name}_{gtype}", used)
                cmd = ["ogr2ogr", "-f", "GPKG", out_path, src, "-nln", table, "-where", where,
                       "-nlt", nlt, "-skipfailures"]
                if os.path.exists(out_path):
                    cmd.insert(1, "-update")
                else:
                    # 1.2 rather than GDAL's 1.4: QGIS LTR and ArcGIS Pro read it fully
                    cmd += ["-dsco", "VERSION=1.2"]
                subprocess.run(cmd, check=True, capture_output=True)
                combos = set(layer.features.annotate(t=GeometryType("geom")).filter(t__in=GEOM_TYPES[gtype])
                             .values_list("risa_type", "risa_status").distinct())
                styles.append((table, layer.name, qml.layer_qml(gtype, combos, layer.style or {},
                                                                analysis=layer.kind == "analysis")))
    if styles:
        write_styles(out_path, styles)
    return out_path


def write_styles(gpkg: str, styles: list[tuple[str, str, str]]) -> None:
    """QGIS's layer_styles table, which QGIS reads when it opens a layer (useAsDefault)."""
    with sqlite3.connect(gpkg) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS layer_styles (
            id INTEGER PRIMARY KEY AUTOINCREMENT, f_table_catalog TEXT(256), f_table_schema TEXT(256),
            f_table_name TEXT(256), f_geometry_column TEXT(256), styleName TEXT(30), styleQML TEXT,
            styleSLD TEXT, useAsDefault BOOLEAN, description TEXT, owner TEXT(30), ui TEXT(30),
            update_time DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))""")
        db.execute("""INSERT OR IGNORE INTO gpkg_contents (table_name, data_type, identifier, description)
            VALUES ('layer_styles', 'attributes', 'layer_styles', 'QGIS styles: RISA symbology')""")
        for table, name, style in styles:
            geom_col = db.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name = ?",
                                  (table,)).fetchone()[0]
            db.execute("""INSERT INTO layer_styles (f_table_catalog, f_table_schema, f_table_name, f_geometry_column,
                styleName, styleQML, styleSLD, useAsDefault, description, owner, ui)
                VALUES ('', '', ?, ?, ?, ?, '', 1, 'RISA symbology, from the RISA Dashboard', '', '')""",
                       (table, geom_col, name[:30], style))
