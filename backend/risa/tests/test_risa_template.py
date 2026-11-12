"""The RISA XLSForm template in the dashboard: the preset field map, submissions to
features, an uploaded Kobo CSV export, and page 2 and the summary with the new types.

The fixtures in fixtures/ are real: risa_asset.json is /api/v2/assets/<uid>/ and
risa_submissions.json /api/v2/assets/<uid>/data/ for the template's test project on
kf.kobotoolbox.org (templates/xlsform/fixtures/, 40 submissions), and risa_export.csv its
CSV export (XML values and headers, groups kept, ";"). The tests check the data contract
(plans/xlsform-template-and-sop.md), not the fixtures' particular answers."""

import json
import re
from pathlib import Path

import pytest
from django.contrib.gis.geos import Point

from risa import ingest, kobo, page2
from risa.models import Feature, KoboSource, Layer, Product, Response, Site
from risa.summary import site_summary
from risa.symbology import classify, match_status, match_type, symbology

FIX = Path(__file__).parent / "fixtures"
ASSET = json.loads((FIX / "risa_asset.json").read_text())
SUBS = json.loads((FIX / "risa_submissions.json").read_text())["results"]
STATUSES = {"ok", "partial", "no", "unknown"}
NEW_TYPES = {"bathing", "waste", "safe_space", "lighting", "energy", "hazard", "market"}


def questions():
    return kobo.form_questions(ASSET)


def test_risa_form_is_recognised_by_form_id_or_questions():
    assert kobo.form_id(ASSET).startswith("risa_obs")
    assert kobo.is_risa_form(ASSET)
    content = ASSET["content"]
    # A country's copy
    assert kobo.is_risa_form({"content": {**content, "settings": {"id_string": "risa_obs_bhs"}}})
    # Renamed, but with the template's questions; settings as a one-row list
    assert kobo.is_risa_form({"content": {**content, "settings": [{"form_id": "bahamas_dorian"}]}})
    # Another form
    other = {"content": {"survey": [{"type": "geopoint", "name": "gps"}, {"type": "text", "name": "obs"}], "choices": []}}
    assert not kobo.is_risa_form(other)
    assert kobo.field_map_for(other).get("preset", "") == ""


def test_risa_field_map_comes_from_the_contract():
    fm = kobo.field_map_for(ASSET)
    assert fm["preset"] == "risa"
    assert (fm["geo"], fm["type"], fm["status"], fm["label"]) == ("obs/location", "obs/feature_type", "obs/status", "obs/feature_id")
    assert (fm["note"], fm["count"]) == ("note", "obs/count")
    assert kobo.is_risa_map(fm)
    # Choice names are RISA codes: identity maps, kept so they can be edited
    types = symbology()["types"]
    assert fm["type_map"] and all(fm["type_map"][c] == c for c in fm["type_map"])
    assert set(fm["type_map"]) <= set(types)
    assert fm["status_map"] == {s: s for s in STATUSES}
    assert "username" in fm["sensitive"]
    assert fm["choice_labels"]["obs/status"]["unknown"]


def test_the_fixtures_cover_every_status_and_the_new_types():
    assert {s["obs/status"] for s in SUBS} == STATUSES
    assert NEW_TYPES <= {s["obs/feature_type"] for s in SUBS}


@pytest.mark.parametrize("sub", SUBS, ids=lambda s: f"{s['obs/feature_type']}-{s['obs/status']}")
def test_risa_submission_to_feature(sub):
    fm = kobo.field_map_for(ASSET)
    g = kobo.geometry(sub, fm)
    lat, lon = (float(x) for x in sub["obs/location"].split()[:2])
    assert (round(g.x, 6), round(g.y, 6)) == (round(lon, 6), round(lat, 6))
    f = kobo.to_feature_fields(sub, fm)
    assert f["risa_type"] == sub["obs/feature_type"] and f["risa_type"] in symbology()["types"]
    assert f["risa_status"] == sub["obs/status"]
    assert f["label"] == sub.get("obs/feature_id", "")
    p = f["properties"]
    assert p.get("note") == (sub.get("note") or None)
    assert p.get("count") == (int(sub["obs/count"]) if sub.get("obs/count") else None)
    assert len(p["_photos"]) == sum(str(a.get("mimetype", "")).startswith("image/") for a in sub.get("_attachments", []))
    for k in ("username", "deviceid", "start_geopoint", "_submitted_by", "meta/instanceID"):
        assert k not in p
    labels = fm["choice_labels"]
    assert p["obs/feature_type:label"] == labels["obs/feature_type"][sub["obs/feature_type"]]
    assert f["observed_at"] is not None


def test_select_multiple_keeps_the_answer_and_joins_the_labels():
    fm = kobo.field_map_for(ASSET)
    multi = [q["path"] for q in questions() if q["type"] == "select_multiple"]
    subs = [(s, q) for s in SUBS for q in multi if s.get(q)]
    assert subs
    for sub, q in subs:
        p = kobo.to_feature_fields(sub, fm)["properties"]
        assert p[q] == sub[q]
        assert p[f"{q}:label"] == ", ".join(fm["choice_labels"][q][c] for c in sub[q].split())
    # The RISA map's type and status are never select_multiple
    assert not {fm["type"], fm["status"]} & set(multi)


def test_photo_attachments_only_images():
    fm = kobo.field_map_for(ASSET)
    sub = next(s for s in SUBS if any(a["mimetype"].startswith("image/") for a in s["_attachments"]))
    photo = kobo.to_feature_fields(sub, fm)["properties"]["_photos"][0]
    att = next(a for a in sub["_attachments"] if a["mimetype"].startswith("image/"))
    assert photo == {"id": att.get("id") or att["uid"], "name": att["media_file_basename"], "url": att["download_small_url"],
                     "large": att["download_large_url"]}


def test_legacy_codes_and_labels_map_to_risa_types():
    for code, t in [("wash_bathing", "bathing"), ("wash_waste_bin", "waste"), ("prot_safe_space_women", "safe_space"),
                    ("prot_safe_space_children", "cfs"), ("prot_site_management", "registration"),
                    ("prot_entry_point", "registration"), ("hlth_health_post", "health"), ("shlt_shelter_collective", "shelter"),
                    ("wash_lighting_solar", "lighting"), ("energy_available", "energy"), ("storage_msu_space", "storage"),
                    ("helipad", "landing"), ("environmental_hazard", "hazard"), ("marketplace", "market"),
                    ("access_constraint", "choke"), ("wash_water_tap_stand", "water"), ("Iluminación", "lighting"),
                    ("Mercado", "market"), ("Déchets", "waste"), ("Espaço seguro", "safe_space")]:
        assert match_type(code) == t, code
    assert match_status("Can't see") == "unknown" and match_status("Não funciona") == "no"


def test_guess_still_used_for_other_forms_and_finds_note_and_count():
    asset = {"content": {"survey": [
        {"type": "geopoint", "name": "gps"},
        {"type": "select_one", "name": "tipo", "select_from_list_name": "t"},
        {"type": "text", "name": "nombre"},
        {"type": "integer", "name": "how_many_taps"},
        {"type": "text", "name": "comentarios"},
    ], "choices": [{"list_name": "t", "name": "agua", "label": ["Agua"]}, {"list_name": "t", "name": "mercado", "label": ["Mercado"]}]}}
    fm = kobo.field_map_for(asset)
    assert not fm.get("preset")
    assert (fm["geo"], fm["type"], fm["label"], fm["note"], fm["count"]) == ("gps", "tipo", "nombre", "comentarios", "how_many_taps")
    assert fm["type_map"] == {"agua": "water", "mercado": "market"}
    f = kobo.to_feature_fields({"gps": "1 2", "tipo": "mercado", "nombre": "M1", "how_many_taps": "3", "comentarios": "Cerrado"}, fm)
    assert f["properties"]["note"] == "Cerrado" and f["properties"]["count"] == 3


@pytest.fixture
def site():
    r = Response(name="T", slug="t")
    r.key = r.set_edit_key()
    r.save()
    return Site.objects.create(response=r, name="Camp", slug="camp")


@pytest.mark.django_db
def test_sync_writes_one_feature_per_submission(site, monkeypatch):
    lyr = Layer.objects.create(site=site, name="Kobo", kind="kobo", status="ready")
    src = KoboSource.objects.create(layer=lyr, server_url="https://kf.kobotoolbox.org", asset_uid=ASSET["uid"],
                                    token_encrypted=kobo.encrypt_token("t"), field_map=kobo.field_map_for(ASSET))
    monkeypatch.setattr(kobo, "_get", lambda c, path, **params: {"results": SUBS, "next": None})
    assert kobo.sync(src, full=True) == len(SUBS)
    assert lyr.features.count() == len(SUBS)
    assert set(lyr.features.values_list("risa_status", flat=True)) == STATUSES
    # Re-syncing updates, never duplicates
    kobo.sync(src, full=True)
    assert lyr.features.count() == len(SUBS)


@pytest.mark.django_db
def test_mapping_away_from_the_template_drops_the_preset(site, monkeypatch):
    from django.test import Client

    from risa import tasks

    monkeypatch.setattr(tasks.sync_kobo, "defer", lambda **kw: None)
    lyr = Layer.objects.create(site=site, name="Kobo", kind="kobo", status="ready")
    src = KoboSource.objects.create(layer=lyr, server_url="https://kf.kobotoolbox.org", asset_uid=ASSET["uid"],
                                    token_encrypted=kobo.encrypt_token("t"), field_map=kobo.field_map_for(ASSET))
    c = Client(headers={"X-Edit-Key": site.response.key})
    c.patch(f"/api/layers/{lyr.id}/kobo", {"field_map": {"type_map": {**src.field_map["type_map"], "other": "water"}}},
            content_type="application/json")
    src.refresh_from_db()
    assert src.field_map["preset"] == "risa" and src.field_map["type_map"]["other"] == "water"
    c.patch(f"/api/layers/{lyr.id}/kobo", {"field_map": {"label": "obs/status_reason"}}, content_type="application/json")
    src.refresh_from_db()
    assert src.field_map["preset"] == ""


def _export(tmp_path, sep="/"):
    text = (FIX / "risa_export.csv").read_text()
    if sep != "/":
        head, rest = text.split("\n", 1)
        text = head.replace("/", sep) + "\n" + rest
    path = tmp_path / "export.csv"
    path.write_text(text)
    return str(path)


def test_kobo_export_columns_are_recognised(tmp_path):
    header = ingest.csv_header(_export(tmp_path))
    ex = ingest.kobo_export(header)
    assert (ex["lat"], ex["lon"]) == ("obs/_location_latitude", "obs/_location_longitude")
    assert ex["field_map"] == {"note": "note", "count": "obs/count"}
    # Older exports put the underscore first: _obs/location_latitude
    old = [re.sub(r"^(obs|visit)/_", r"_\1/", h) for h in header]
    assert ingest.kobo_export(old)["lat"] == "_obs/location_latitude"
    # Without groups: _location_latitude
    flat = [re.sub(r"^(?:obs|visit)/", "", h) for h in header]
    ex = ingest.kobo_export(flat)
    assert (ex["lat"], ex["lon"]) == ("_location_latitude", "_location_longitude")
    assert ingest.kobo_export(["lat", "lon", "name"]) is None
    assert classify({"obs-feature_type": "bathing", "obs-status": "no", "obs-feature_id": "BA-01"}) == ("bathing", "no", "BA-01")
    assert classify({"obs.feature_type": "Market", "obs.status": "Partly working", "obs.feature_id": "MK-1"}) == ("market", "partial", "MK-1")


@pytest.mark.django_db
@pytest.mark.parametrize("sep", ["/", "-", "."])
def test_uploaded_kobo_export_maps_type_status_and_label(site, tmp_path, sep):
    lyr = Layer.objects.create(site=site, name="Export", kind="vector")
    ingest.ingest_vector(lyr, _export(tmp_path, sep))
    feats = list(lyr.features.all())
    assert len(feats) == len(SUBS)
    by_label = {f.label: f for f in feats}
    for sub in SUBS:
        f = by_label[sub["obs/feature_id"]]
        assert (f.risa_type, f.risa_status) == (sub["obs/feature_type"], sub["obs/status"])
        lat, lon = (float(x) for x in sub["obs/location"].split()[:2])
        # The observation's location, not start_geopoint
        assert (round(f.geom.x, 4), round(f.geom.y, 4)) == (round(lon, 4), round(lat, 4))
        assert (f.properties.get("note") or None) == (sub.get("note") or None)
        if sub.get("obs/count"):
            assert f.properties["count"] == int(sub["obs/count"])
        assert "username" not in f.properties and "_submitted_by" not in f.properties
        assert not any(k.startswith("_start_geopoint") for k in f.properties)


@pytest.mark.django_db
def test_page2_and_summary_with_the_new_types(site):
    lyr = Layer.objects.create(site=site, name="Kobo", kind="kobo", status="ready")
    ai = Layer.objects.create(site=site, name="Detected", kind="analysis", status="ready")
    pt = lambda x, y: Point(-77.35 + x, 25.04 + y, srid=4326)  # noqa: E731
    for i, (t, st, label) in enumerate([("bathing", "no", "BA-01"), ("bathing", "ok", "BA-02"), ("waste", "partial", "WS-01"),
                                        ("safe_space", "no", "SS-01"), ("lighting", "no", "LI-01"), ("energy", "ok", "EN-01"),
                                        ("market", "no", "MK-01"), ("water", "ok", "WP-01")]):
        Feature.objects.create(layer=lyr, geom=pt(0.001 * i, 0.002), risa_type=t, risa_status=st, label=label,
                               properties={"note": f"note {label}", "count": 2})
    # A hazard observed as a point, with two shelters 10 m away and one 200 m away
    Feature.objects.create(layer=lyr, geom=pt(0, 0), risa_type="hazard", risa_status="no", label="HZ-01",
                           properties={"note": "Eroded bank"})
    for dx in (0.0001, -0.0001, 0.002):
        Feature.objects.create(layer=ai, geom=pt(dx, 0), risa_type="shelter", properties={"review": "accepted"})

    s = site_summary(site)
    services = {x["type"]: x for x in s["services"]}
    assert "hazard" not in services
    assert services["bathing"]["total"] == 2 and services["bathing"]["no"] == 1
    assert services["safe_space"]["label"] == "Women's safe space"
    assert {"waste", "lighting", "energy", "market"} <= set(services)

    gaps = page2.suggest_gaps(Product.objects.create(site=site, view={}), [str(lyr.id), str(ai.id)])
    who = {g["title"].split(":")[0]: g["who"] for g in gaps}
    assert who.get("Bathing facility") == "WASH cluster"
    assert who.get("Women's safe space") == "Protection (GBV AoR)"
    hz = next(g for g in gaps if g["title"].startswith("HZ-01"))
    assert hz["title"] == "HZ-01 near 2 shelters" and hz["who"] == "Site management · CCCM" and hz["status"] == "no"
    assert not any(g["title"].startswith("Hazard:") for g in gaps)
    assert len(gaps) == 5

    d = page2.build(Product.objects.create(site=site, view={}), {"product": {}}, s)
    assert "hazard" not in [x["type"] for x in d["services"]]


def test_every_type_has_a_glyph_a_label_and_a_cluster_in_every_language():
    types = symbology()["types"]
    for t in NEW_TYPES:
        assert types[t]["glyph"] and types[t]["label"]
        assert t in symbology()["synonyms"]["type"]
        for lang in page2.WHO:
            assert t in page2.WHO[lang]
    assert set(page2.WHO["en"]) == set(page2.WHO["es"]) == set(page2.WHO["fr"])
