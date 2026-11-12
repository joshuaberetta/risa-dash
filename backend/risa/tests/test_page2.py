import pytest
from django.contrib.gis.geos import LineString, Point, Polygon
from django.test import Client

from risa import page2
from risa.models import Feature, Layer, Product, Response, Site
from risa.summary import site_summary


def sq(x, y, d):
    return Polygon(((x, y), (x + d, y), (x + d, y + d), (x, y + d), (x, y)), srid=4326)


@pytest.fixture
def site():
    r = Response(name="T", slug="t", household_size=4.5)
    r.key = r.set_edit_key()
    r.save()
    s = Site.objects.create(response=r, name="Camp", slug="camp")
    layout = Layer.objects.create(site=s, name="Layout", kind="vector")
    Feature.objects.create(layer=layout, geom=sq(0, 0, 0.001), risa_type="block", label="Block A")
    Feature.objects.create(layer=layout, geom=sq(0.002, 0, 0.001), risa_type="block", label="Block B")
    Feature.objects.create(layer=layout, geom=sq(0.0015, -0.0002, 0.001), risa_type="flood", label="Flooded canal")
    Feature.objects.create(layer=layout, geom=LineString((0, 0), (0.003, 0), srid=4326), risa_type="route", risa_status="no",
                           label="R3", properties={"note": "Canal path flooded"})
    Feature.objects.create(layer=layout, geom=LineString((0, 1), (0.003, 1), srid=4326), risa_type="route", risa_status="partial", label="R2")
    for i, st in enumerate(["ok", "no", "no", "partial"]):
        Feature.objects.create(layer=layout, geom=Point(i * 0.0002, 0.0005, srid=4326), risa_type="water", risa_status=st, label=f"WP-0{i + 1}")
    Feature.objects.create(layer=layout, geom=Point(0.0001, 0.0001, srid=4326), risa_type="storage", risa_status="ok", label="WH-01",
                           properties={"note": "Dry"})
    ai = Layer.objects.create(site=s, name="Detected", kind="analysis")
    # Three accepted shelters in A, two in B (one in the flood), one suggested, one rejected
    for x, review in [(0.0002, "accepted"), (0.0004, "accepted"), (0.0006, "accepted"), (0.0021, "accepted"),
                      (0.0024, "accepted"), (0.0008, "suggested"), (0.0026, "rejected")]:
        Feature.objects.create(layer=ai, geom=sq(x, 0.0001, 0.00004), risa_type="shelter", properties={"review": review})
    return s


@pytest.mark.django_db
def test_shelters_by_block_count_accepted_shelters_in_drawn_blocks(site):
    layers = list(site.layers.all())
    assert page2.shelters_by_block(layers) == [{"label": "Block A", "shelters": 3}, {"label": "Block B", "shelters": 2}]


@pytest.mark.django_db
def test_suggested_gaps_most_urgent_first(site):
    p = Product.objects.create(site=site, view={})
    gaps = page2.suggest_gaps(p)
    titles = [g["title"] for g in gaps]
    assert titles[0] in ("Access: R3 closed", "Water point: 2 of 4 not working")
    assert "Water point: 2 of 4 not working" in titles
    wp = next(g for g in gaps if g["title"].startswith("Water"))
    assert wp["who"] == "WASH cluster" and "WP-02, WP-03" in wp["text"] and wp["status"] == "no"
    flood = next(g for g in gaps if "Flooded canal" in g["title"])
    assert "Block B" in flood["text"] and flood["title"] == "Flooded canal over 2 shelters"
    assert titles[-1] == "Access restricted on R2"


@pytest.mark.django_db
def test_page2_data_and_the_api(site):
    p = Product.objects.create(site=site, view={}, pages=[1, 2],
                               findings={"reach_note": "Use R1", "gaps": [{"status": "no", "title": "Water", "text": "", "who": "WASH"}]})
    d = page2.build(p, {"product": {}}, site_summary(site))
    assert d["verdict"] == "no" and d["routes_open"] == "0 of 2 access routes open"
    assert d["logistics"][0]["label"] == "WH-01" and d["reach_note"] == "Use R1"
    assert d["households"] == "5" and d["people"] == "22"  # 5 shelters x 4.5
    assert [s["label"] for s in d["services"]] == ["Water point"]
    c = Client(headers={"X-Edit-Key": site.response.key})
    assert len(c.get(f"/api/products/{p.id}/suggested-gaps").json()) >= 3
    res = c.patch(f"/api/products/{p.id}", {"pages": [2, 7], "findings": {"gaps": [{"status": "bad", "title": "x" * 400}]}},
                  content_type="application/json").json()
    assert res["pages"] == [1, 2] and res["findings"]["gaps"][0]["status"] == "partial"
    assert len(res["findings"]["gaps"][0]["title"]) == 300
    r = c.patch("/api/responses/t", {"household_size": 50}, content_type="application/json").json()
    assert r["household_size"] == 20
