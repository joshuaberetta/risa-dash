import sqlite3
import xml.etree.ElementTree as ET

import pytest
from django.contrib.gis.geos import LineString, Point, Polygon

from risa import exports
from risa.models import Feature, Layer, Response, Site


@pytest.mark.django_db
def test_geopackage_carries_qgis_styles(tmp_path):
    r = Response(name="T", slug="t")
    r.set_edit_key()
    r.save()
    site = Site.objects.create(response=r, name="S", slug="s")
    lyr = Layer.objects.create(site=site, name="Site layout", kind="vector", style={"opacity": 0.8})
    Feature.objects.create(layer=lyr, geom=Point(1, 1, srid=4326), risa_type="water", risa_status="no", label="WP-01")
    Feature.objects.create(layer=lyr, geom=Point(1, 2, srid=4326), risa_type="water", risa_status="", label="WP-02")
    Feature.objects.create(layer=lyr, geom=LineString((0, 0), (1, 1), srid=4326), risa_type="route", risa_status="partial")
    Feature.objects.create(layer=lyr, geom=Polygon(((0, 0), (1, 0), (1, 1), (0, 0)), srid=4326), risa_type="flood")
    ai = Layer.objects.create(site=site, name="Detected shelters", kind="analysis")
    Feature.objects.create(layer=ai, geom=Polygon(((0, 0), (1, 0), (1, 1), (0, 0)), srid=4326), risa_type="shelter",
                           properties={"ai_class": "shelter", "review": "suggested"})

    path = str(tmp_path / "s.gpkg")
    exports.site_geopackage(site, path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 10200
        styles = {t: (g, q, d) for t, g, q, d in db.execute(
            "SELECT f_table_name, f_geometry_column, styleQML, useAsDefault FROM layer_styles")}
        assert db.execute("SELECT data_type FROM gpkg_contents WHERE table_name = 'layer_styles'").fetchone() == ("attributes",)
    assert set(styles) == {"site_layout_points", "site_layout_lines", "site_layout_polygons", "detected_shelters"}
    assert all(g == "geom" and d == 1 for g, _, d in styles.values())

    rules = lambda t: [(x.get("label"), x.get("filter")) for x in ET.fromstring(styles[t][1]).iter("rule")]  # noqa: E731
    # Only what's in the table, a missing status as Not assessed, and a fallback
    assert [label for label, _ in rules("site_layout_points")] == ["Water point · Not working", "Water point · Not assessed", "Other"]
    assert rules("site_layout_points")[-1][1] == "ELSE"
    assert [label for label, _ in rules("site_layout_lines")][0] == "Access route · Partly"
    assert [label for label, _ in rules("site_layout_polygons")][0] == "Flooded area"
    assert [label for label, _ in rules("detected_shelters")] == ["Shelter · suggested", "Shelter · accepted"]
    pts = ET.fromstring(styles["site_layout_points"][1])
    assert pts.find("layerOpacity").text == "0.8"
    assert pts.find("labeling/settings/text-style").get("fieldName") == "risa_label"
    # The point symbols are page 1's, embedded
    assert any(o.get("value", "").startswith("base64:") for o in pts.iter("Option"))
    # Partly: dashed
    line = ET.fromstring(styles["site_layout_lines"][1])
    assert any(o.get("name") == "use_custom_dash" and o.get("value") == "1" for o in line.iter("Option"))


@pytest.mark.django_db
def test_geojson_and_csv_downloads(client):
    import csv
    import io
    import json
    import zipfile

    r = Response(name="T", slug="t")
    r.set_edit_key()
    r.save()
    site = Site.objects.create(response=r, name="Camp A", slug="camp-a")
    lyr = Layer.objects.create(site=site, name="Water points", kind="kobo")
    Feature.objects.create(layer=lyr, geom=Point(35.25, -19.5, srid=4326), risa_type="water", risa_status="no",
                           label="WP-01", properties={"note": "dry, «since Monday»", "tags": ["a"]})
    Feature.objects.create(layer=lyr, geom=Polygon(((0, 0), (2, 0), (2, 2), (0, 0)), srid=4326), risa_type="flood")
    Layer.objects.create(site=site, name="Empty", kind="vector")

    res = client.get(f"/api/layers/{lyr.id}/export.csv")
    assert res["Content-Disposition"] == 'attachment; filename="t_camp-a_Water_points.csv"'
    text = res.content.decode("utf-8")
    assert text.startswith("﻿")
    rows = list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))
    wp = next(x for x in rows if x["label"] == "WP-01")
    assert (wp["type_label"], wp["status"], wp["status_label"]) == ("Water point", "no", "Closed / not working")
    assert (wp["longitude"], wp["latitude"], wp["note"], wp["tags"]) == ("35.25", "-19.5", "dry, «since Monday»", '["a"]')
    flood = next(x for x in rows if x["type"] == "flood")
    assert flood["geometry_wkt"].startswith("POLYGON") and float(flood["longitude"]) > 1

    gj = json.loads(client.get(f"/api/layers/{lyr.id}/export.geojson").content)
    assert len(gj["features"]) == 2 and gj["features"][0]["properties"]["risa_id"]
    assert client.get(f"/api/layers/{lyr.id}/export.shp").status_code == 404

    res = client.get(f"/api/sites/{site.id}/export-csv.zip")
    with zipfile.ZipFile(io.BytesIO(b"".join(res.streaming_content))) as z:
        assert z.namelist() == ["water_points.csv"]
    res = client.get(f"/api/sites/{site.id}/export-geojson.zip")
    with zipfile.ZipFile(io.BytesIO(b"".join(res.streaming_content))) as z:
        assert z.namelist() == ["water_points.geojson"]
