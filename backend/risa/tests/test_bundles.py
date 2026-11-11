import json
import zipfile

import pytest
from django.contrib.gis.geos import Point, Polygon
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client

from risa import bundles, tasks
from risa.models import (
    Feature,
    KoboSource,
    Layer,
    Product,
    ProductVersion,
    Response,
    Site,
    Transfer,
    hash_key,
)


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.STORAGE = "filesystem"
    return tmp_path


def make_response():
    r = Response(name="Floods", slug="floods", country="MOZ")
    key = r.set_edit_key()
    r.save()
    site = Site.objects.create(response=r, name="Camp A", slug="camp-a", default_view={"center": [35, -19], "zoom": 16})
    vec = Layer.objects.create(site=site, name="Observations", kind="vector", style={"preset": "risa"}, z_order=2)
    Feature.objects.create(layer=vec, geom=Point(35.001, -19.001, srid=4326), risa_type="water", risa_status="no",
                           label="WP-01", properties={"note": "dry"})
    Feature.objects.create(layer=vec, geom=Polygon(((35, -19), (35.01, -19), (35.01, -19.01), (35, -19)), srid=4326),
                           risa_type="block", label="Block A")
    cog = Layer.objects.create(site=site, name="Ortho", kind="raster", z_order=1)
    cog.source = default_storage.save(f"layers/{cog.id}/cog.tif", ContentFile(b"II*\x00fake cog"))
    cog.save()
    kobo = Layer.objects.create(site=site, name="Kobo", kind="kobo")
    KoboSource.objects.create(layer=kobo, server_url="https://kf.kobotoolbox.org", asset_uid="aBc",
                              token_encrypted="secret-blob", field_map={"type": "q1"})
    p = Product.objects.create(site=site, code="MZ01", view={"basemap": "none", "layers": [{"id": str(vec.id)}]})
    ProductVersion.objects.create(product=p, n=1, status="ready", snapshot={"summary": {}},
                                  pdf_key=default_storage.save(f"products/{p.id}/v1.pdf", ContentFile(b"%PDF-1.7 test")))
    return r, key


@pytest.mark.django_db
def test_round_trip_keeps_ids_files_and_edit_key(media):
    r, key = make_response()
    rid, fids = r.id, set(Feature.objects.values_list("id", flat=True))
    path = str(media / "b.zip")
    m = bundles.export_bundle(r, path)
    with zipfile.ZipFile(path) as z:
        assert z.namelist()[-1] == "manifest.json"
        data = json.loads(z.read("response.json"))
    assert "secret-blob" not in json.dumps(data)
    assert any(n.endswith("cog.tif") for n in m["files"]) and any(n.startswith("gpkg/") for n in m["files"])

    r.delete()
    # As on another instance: the COG comes from the bundle
    default_storage.delete(next(n.removeprefix("files/") for n in m["files"] if n.endswith("cog.tif")))
    out = bundles.import_bundle(path)
    assert out["created"] and out["sites"] == 1 and out["layers"] == 3 and out["features"] == 2
    r = Response.objects.get(id=rid)
    assert r.slug == "floods" and r.check_edit_key(key)
    assert set(Feature.objects.values_list("id", flat=True)) == fids
    cog = Layer.objects.get(kind="raster")
    assert default_storage.open(cog.source).read() == b"II*\x00fake cog"
    v = ProductVersion.objects.get()
    assert v.status == "ready" and default_storage.open(v.pdf_key).read().startswith(b"%PDF")
    k = KoboSource.objects.get()
    assert k.token_encrypted == "" and not k.auto_sync and k.field_map == {"type": "q1"}

    # Again: nothing changes
    again = bundles.import_bundle(path, edit_key_hash=hash_key(key))
    assert not again["created"] and Feature.objects.count() == 2 and Layer.objects.count() == 3
    assert ProductVersion.objects.count() == 1


@pytest.mark.django_db
def test_import_into_an_existing_response_needs_its_key(media):
    r, key = make_response()
    path = str(media / "b.zip")
    bundles.export_bundle(r, path)
    with pytest.raises(bundles.BundleError, match="edit key"):
        bundles.import_bundle(path)
    with pytest.raises(bundles.BundleError, match="edit key"):
        bundles.import_bundle(path, edit_key_hash=hash_key("wrong"))
    # Local changes since the export are replaced by the bundle's, local extras kept
    Feature.objects.filter(label="WP-01").update(risa_status="ok")
    extra = Site.objects.create(response=r, name="Camp B", slug="camp-b")
    bundles.import_bundle(path, edit_key_hash=hash_key(key))
    assert Feature.objects.get(label="WP-01").risa_status == "no"
    assert Site.objects.filter(id=extra.id).exists()


@pytest.mark.django_db
def test_without_imagery_keeps_the_local_imagery(media):
    r, key = make_response()
    path = str(media / "b.zip")
    m = bundles.export_bundle(r, path, imagery=False)
    assert not any(n.endswith(".tif") for n in m["files"])
    Layer.objects.filter(kind="raster").update(name="Ortho, local")
    bundles.import_bundle(path, edit_key_hash=hash_key(key))
    assert Layer.objects.get(kind="raster").name == "Ortho, local"


@pytest.mark.django_db
def test_damaged_or_cut_off_bundles_are_refused(media):
    r, _ = make_response()
    path = str(media / "b.zip")
    bundles.export_bundle(r, path)
    with zipfile.ZipFile(path) as z:
        items = {n: z.read(n) for n in z.namelist()}
    r.delete()

    bad = str(media / "bad.zip")
    with zipfile.ZipFile(bad, "w") as z:
        for n, b in items.items():
            z.writestr(n, b.replace(b"WP-01", b"WP-99") if n.startswith("features/") else b)
    with pytest.raises(bundles.BundleError, match="damaged"):
        bundles.import_bundle(bad)

    cut = str(media / "cut.zip")
    with zipfile.ZipFile(cut, "w") as z:
        for n, b in items.items():
            if n != "manifest.json":
                z.writestr(n, b)
    with pytest.raises(bundles.BundleError, match="manifest"):
        bundles.import_bundle(cut)
    assert not Response.objects.exists()


@pytest.mark.django_db
def test_rows_cannot_point_at_other_files(media):
    r, _ = make_response()
    other = Layer.objects.create(site=r.sites.get(), name="Other", kind="raster")
    other.source = default_storage.save("layers/00000000-0000-0000-0000-000000000000/cog.tif", ContentFile(b"x"))
    other.save()
    path = str(media / "b.zip")
    bundles.export_bundle(r, path)
    r.delete()
    bundles.import_bundle(path)
    # The layer's key isn't under its own ID, so it isn't imported
    assert not Layer.objects.filter(id=other.id).exists()


@pytest.mark.django_db
def test_api_export_and_import(media, monkeypatch, settings):
    monkeypatch.setattr(tasks.export_bundle, "defer", lambda **kw: tasks.export_bundle(**kw))
    monkeypatch.setattr(tasks.import_bundle, "defer", lambda **kw: tasks.import_bundle(**kw))
    r, key = make_response()
    c = Client(headers={"X-Edit-Key": key})
    assert Client().post("/api/responses/floods/bundles", {}, content_type="application/json").status_code == 403
    t = c.post("/api/responses/floods/bundles", {"imagery": True}, content_type="application/json").json()
    t = Client().get(f"/api/transfers/{t['id']}").json()
    assert t["status"] == "ready", t["error"]
    body = b"".join(Client().get(t["download"]).streaming_content)
    assert body.startswith(b"PK")
    assert Client().get("/media/" + Transfer.objects.get().file_key).status_code == 404

    # Import on an instance with a create key
    settings.CREATE_KEY = "ck"
    r.delete()
    assert Client().post("/api/bundles/uploads", {"filename": "b.zip", "size": len(body)},
                         content_type="application/json").status_code == 403
    up = Client(headers={"X-Create-Key": "ck"})
    u = up.post("/api/bundles/uploads", {"filename": "b.zip", "size": len(body)}, content_type="application/json").json()
    for n in range(u["parts"]):
        part = body[n * u["chunk_size"]:(n + 1) * u["chunk_size"]]
        assert up.put(f"/api/uploads/{u['id']}/parts/{n}", part, content_type="application/octet-stream").status_code == 200
    t = up.post(f"/api/uploads/{u['id']}/complete").json()
    t = Client().get(f"/api/transfers/{t['id']}").json()
    assert t["status"] == "ready", t["error"]
    assert t["response"] == "floods" and t["result"]["features"] == 2
    assert Response.objects.get().check_edit_key(key)


@pytest.mark.django_db
def test_old_bundles_are_cleaned_up(media):
    from datetime import timedelta

    from django.utils import timezone

    r, _ = make_response()
    t = Transfer.objects.create(kind="export", response=r, status="ready",
                                file_key=default_storage.save("bundles/x/b.zip", ContentFile(b"PK")))
    keep = Transfer.objects.create(kind="export", response=r)
    Transfer.objects.filter(id=t.id).update(created_at=timezone.now() - timedelta(days=8))
    tasks.clean_bundles(0)
    assert list(Transfer.objects.all()) == [keep]
