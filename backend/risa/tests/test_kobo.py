import pytest
from django.test import override_settings

from risa import kobo
from risa.symbology import classify, match_status, match_type

ASSET = {
    "content": {
        "survey": [
            {"type": "start", "name": "start"},
            {"type": "begin_group", "name": "obs"},
            {"type": "geopoint", "name": "location", "label": ["Location"]},
            {"type": "select_one", "name": "infra_type", "select_from_list_name": "types", "label": ["Type"]},
            {"type": "select_one", "name": "functionality", "select_from_list_name": "func", "label": ["Status"]},
            {"type": "text", "name": "facility_name", "label": ["Name"]},
            {"type": "text", "name": "contact_phone", "label": ["Phone"]},
            {"type": "end_group"},
        ],
        "choices": [
            {"list_name": "types", "name": "water_point", "label": ["Water point"]},
            {"list_name": "types", "name": "letrina", "label": ["Letrina"]},
            {"list_name": "types", "name": "clinic", "label": ["Clinic"]},
            {"list_name": "func", "name": "functional", "label": ["Functional"]},
            {"list_name": "func", "name": "partially_functional", "label": ["Partially"]},
            {"list_name": "func", "name": "not_working", "label": ["Not working"]},
        ],
    }
}


def test_status_and_type_matching():
    assert match_status("Partly working") == "partial"
    assert match_status("No funciona") == "no"
    assert match_status("Abierto") == "ok"
    assert match_status("banana") == ""
    assert match_type("Puesto de salud") == "health"
    assert match_type("letrinas_bloque_a") == "latrine"
    assert classify({"Tipo": "Agua", "Estado": "cerrado", "Nombre": "WP-1"}) == ("water", "no", "WP-1")


def test_guess_field_map_finds_questions_and_maps_choices():
    fm = kobo.guess_field_map(kobo.form_questions(ASSET))
    assert fm["geo"] == "obs/location"
    assert fm["type"] == "obs/infra_type"
    assert fm["status"] == "obs/functionality"
    assert fm["label"] == "obs/facility_name"
    assert fm["status_map"] == {"functional": "ok", "partially_functional": "partial", "not_working": "no"}
    assert fm["type_map"]["water_point"] == "water"
    assert fm["type_map"]["letrina"] == "latrine"
    assert "obs/contact_phone" in fm["sensitive"]


def test_submission_to_feature():
    fm = kobo.guess_field_map(kobo.form_questions(ASSET))
    sub = {
        "_id": 7, "_uuid": "u7", "obs/location": "18.5596 -72.3273 40 5", "obs/infra_type": "letrina",
        "obs/functionality": "partially_functional", "obs/facility_name": "LT-01", "obs/contact_phone": "+509 0000",
        "_attachments": [{"id": 1, "mimetype": "image/jpeg", "download_url": "https://kf.kobotoolbox.org/a/1",
                          "download_small_url": "https://kf.kobotoolbox.org/a/1?s", "media_file_basename": "p.jpg"}],
        "_submission_time": "2026-10-27T10:00:00",
    }
    g = kobo.geometry(sub, fm)
    assert (round(g.x, 4), round(g.y, 4)) == (-72.3273, 18.5596)
    f = kobo.to_feature_fields(sub, fm)
    assert (f["risa_type"], f["risa_status"], f["label"]) == ("latrine", "partial", "LT-01")
    assert "obs/contact_phone" not in f["properties"]
    assert f["properties"]["obs/infra_type:label"] == "Letrina"
    assert f["properties"]["_photos"][0]["url"].endswith("?s")
    # No answer: never a status
    sub2 = {**sub, "obs/functionality": None}
    assert kobo.to_feature_fields(sub2, fm)["risa_status"] == "unknown"


def test_geoshape_becomes_polygon():
    fm = {"geo": "shape"}
    g = kobo.geometry({"shape": "1 1 0 0;1 2 0 0;2 2 0 0;1 1 0 0"}, fm)
    assert g.geom_type == "Polygon"


@override_settings(ALLOWED_SERVERS=["https://kf.kobotoolbox.org", "https://eu.kobotoolbox.org", "http://kf.kobo.local"])
def test_server_allow_list():
    assert kobo.check_server("kf.kobotoolbox.org") == "https://kf.kobotoolbox.org"
    assert kobo.check_server("https://eu.kobotoolbox.org/") == "https://eu.kobotoolbox.org"
    assert kobo.check_server("http://kf.kobo.local") == "http://kf.kobo.local"
    for bad in ("http://kf.kobotoolbox.org", "https://evil.example", "https://kf.kobotoolbox.org/api", "ftp://x"):
        with pytest.raises(kobo.KoboError):
            kobo.check_server(bad)


def test_token_round_trip():
    blob = kobo.encrypt_token("secret-token")
    assert "secret" not in blob
    assert kobo.decrypt_token(blob) == "secret-token"
