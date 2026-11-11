import pytest
from django.contrib.gis.geos import Point, Polygon

from risa import evaluation
from risa.models import Feature, Layer, Response, Site


def sq(x, y, d=0.00004):
    return Polygon(((x, y), (x + d, y), (x + d, y + d), (x, y + d), (x, y)), srid=4326)


@pytest.mark.django_db
def test_precision_recall_against_marked_shelters():
    r = Response(name="T", slug="t")
    r.set_edit_key()
    r.save()
    site = Site.objects.create(response=r, name="S", slug="s")
    ai = Layer.objects.create(site=site, name="Detected", kind="analysis", meta={"model": "m1", "simulated": False})
    ref = Layer.objects.create(site=site, name="Reference", kind="annotations")
    for i, conf in enumerate([0.9, 0.8, 0.4]):           # two right, the third (0.4) on nothing
        Feature.objects.create(layer=ai, geom=sq(i * 0.0001, 0), risa_type="shelter",
                               properties={"ai_class": "shelter", "confidence": conf})
    # A second detection on the same shelter only counts once
    Feature.objects.create(layer=ai, geom=sq(0.000005, 0.000005), risa_type="shelter",
                           properties={"ai_class": "shelter", "confidence": 0.5})
    for x in (0.00002, 0.00012, 0.00032):                # the third is missed
        Feature.objects.create(layer=ref, geom=Point(x, 0.00002, srid=4326), risa_type="shelter")
    # Far outside the reference: not scored
    Feature.objects.create(layer=ai, geom=sq(0.01, 0.01), risa_type="shelter", properties={"ai_class": "shelter", "confidence": 0.9})

    e = evaluation.evaluate(ai, ref)
    assert (e["reference_count"], e["detected"], e["matched"]) == (3, 4, 2)
    assert (e["precision"], e["recall"]) == (0.5, 0.667)
    assert e["reference_kind"] == "points" and e["model"] == "m1"
    at_06 = next(c for c in e["curve"] if c["min_confidence"] == 0.6)
    assert (at_06["detected"], at_06["matched"], at_06["precision"]) == (2, 2, 1.0)
    assert e["best_threshold"] == 0.6
    ai.refresh_from_db()
    assert ai.meta["evaluation"]["f1"] == e["f1"]
    # Scored only inside a given box: the first shelter alone
    e = evaluation.evaluate(ai, ref, bbox=[-0.000001, -0.000001, 0.00005, 0.00005], save=False)
    assert (e["reference_count"], e["matched"]) == (1, 1)


@pytest.mark.django_db
def test_outlines_match_by_overlap():
    r = Response(name="T", slug="t")
    r.set_edit_key()
    r.save()
    site = Site.objects.create(response=r, name="S", slug="s")
    ai = Layer.objects.create(site=site, name="Detected", kind="analysis")
    ref = Layer.objects.create(site=site, name="Reference", kind="vector")
    Feature.objects.create(layer=ai, geom=sq(0, 0), risa_type="shelter", properties={"ai_class": "shelter", "confidence": 0.9})
    Feature.objects.create(layer=ai, geom=sq(0.0001, 0), risa_type="shelter", properties={"ai_class": "shelter", "confidence": 0.9})
    Feature.objects.create(layer=ref, geom=sq(0.000005, 0), risa_type="shelter")              # IoU ~0.78
    Feature.objects.create(layer=ref, geom=sq(0.0001 + 0.00003, 0), risa_type="shelter")     # IoU ~0.14
    e = evaluation.evaluate(ai, ref)
    assert e["matched"] == 1 and e["reference_kind"] == "outlines"
