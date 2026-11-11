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
