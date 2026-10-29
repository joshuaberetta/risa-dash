import numpy as np
import pytest
from django.contrib.gis.geos import Polygon
from django.test import Client

from risa import analysis
from risa.models import Feature, Layer, Response, Site
from risa.summary import site_summary


def test_detect_finds_tarps_not_ground():
    rgb = np.zeros((60, 60, 3), np.uint8)
    rgb[...] = (170, 140, 110)          # tan ground
    rgb[10:20, 10:22] = (205, 208, 210)  # grey sheet roof
    rgb[35:44, 30:40] = (40, 90, 200)    # blue tarp
    rgb[50, 50] = (230, 230, 230)        # speckle
    m = analysis.detect(rgb, np.ones((60, 60), bool))
    assert m[12:18, 12:20].all()
    assert m[37:42, 32:38].all()
    assert m[50, 50] == 0 and m[0:5, 0:5].sum() == 0


def test_score_prefers_tent_sized_compact_shapes():
    tent = analysis.score(16, 0.8, "shelter")
    odd = analysis.score(55, 0.3, "shelter")
    assert 0 < odd < tent < 1


@pytest.mark.django_db
def test_review_and_summary_count_only_accepted():
    r = Response(name="T", slug="t")
    key = r.set_edit_key()
    r.save()
    site = Site.objects.create(response=r, name="S", slug="s")
    lyr = Layer.objects.create(site=site, name="A", kind="analysis", meta={"simulated": True})
    sq = lambda x: Polygon(((x, 0), (x + 0.00003, 0), (x + 0.00003, 0.00003), (x, 0.00003), (x, 0)), srid=4326)  # noqa: E731
    for i, conf in enumerate([0.9, 0.8, 0.5, 0.3]):
        Feature.objects.create(layer=lyr, geom=sq(i * 0.001), risa_type="shelter",
                               properties={"ai_class": "shelter", "confidence": conf, "review": "suggested"})
    assert site_summary(site)["shelters"] == 0
    assert site_summary(site)["pending_review"] == 4
    c = Client(headers={"X-Edit-Key": key})
    res = c.post(f"/api/layers/{lyr.id}/review", {"action": "accept", "min_confidence": 0.7}, content_type="application/json")
    assert res.json() == {"changed": 2}
    s = site_summary(site)
    assert s["shelters"] == 2 and s["pending_review"] == 2
    # Rejecting one and editing another by hand
    low = lyr.features.get(properties__confidence=0.3)
    assert c.patch(f"/api/features/{low.id}", {"review": "rejected"}, content_type="application/json").status_code == 200
    mid = lyr.features.get(properties__confidence=0.5)
    c.patch(f"/api/features/{mid.id}", {"risa_type": "building"}, content_type="application/json")
    mid.refresh_from_db()
    assert mid.properties["review"] == "accepted" and mid.properties["edited"] is True
    assert c.post(f"/api/layers/{lyr.id}/review", {"action": "delete_rejected"}, content_type="application/json").json() == {"changed": 1}
    # Without the key, no review
    assert Client().post(f"/api/layers/{lyr.id}/review", {"action": "accept"}, content_type="application/json").status_code == 403
