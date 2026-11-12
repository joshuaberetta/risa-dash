import io
from pathlib import Path

import numpy as np
import pytest
from django.contrib.gis.geos import Point
from django.core.files.storage import default_storage
from PIL import Image

from risa import kobo, redact
from risa.models import Feature, KoboSource, Layer, Response, Site

# Five of NASA's Commercial Crew astronauts (public domain), with a phone's make, model,
# time and GPS position written in
FACES = (Path(__file__).parent / "fixtures" / "faces.jpg").read_bytes()
needs_model = pytest.mark.skipif(bool(redact.available()), reason="no face model (scripts/fetch-models.sh)")


def jpeg(img: Image.Image, **kw) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", **kw)
    return buf.getvalue()


@needs_model
def test_faces_found_and_hidden():
    img = Image.open(io.BytesIO(FACES)).convert("RGB")
    boxes, scores = redact.find_faces(img)
    assert len(boxes) == 5 and scores.min() >= redact.MIN_SCORE
    out = redact.redact(FACES)
    assert out["faces"] == 5
    before, after = np.asarray(img, np.float32), np.asarray(Image.open(io.BytesIO(out["large"])), np.float32)
    assert before.shape == after.shape
    for x0, y0, x1, y1 in boxes.astype(int):
        face_b, face_a = before[y0:y1, x0:x1], after[y0:y1, x0:x1]
        # Smudged: the detail (differences between neighbouring pixels) is gone
        assert np.abs(np.diff(face_a, axis=1)).mean() < 0.3 * np.abs(np.diff(face_b, axis=1)).mean()
    # The rest is left alone: the flag in the corner
    assert np.abs(before[5:45, 5:60] - after[5:45, 5:60]).mean() < 4


def test_metadata_dropped(monkeypatch):
    monkeypatch.setattr(redact, "find_faces", lambda img: (np.zeros((0, 4)), np.zeros(0)))
    assert Image.open(io.BytesIO(FACES)).getexif().get_ifd(0x8825)  # the fixture has a position
    out = redact.redact(FACES)
    for size, long in (("large", 672), ("thumb", redact.THUMB)):
        im = Image.open(io.BytesIO(out[size]))
        assert len(im.getexif()) == 0 and "exif" not in im.info
        assert max(im.size) == long


def test_photo_turned_upright_first(monkeypatch):
    """Phones store the turn in EXIF: the faces are looked for, and kept, upright."""
    seen = []
    monkeypatch.setattr(redact, "find_faces", lambda img: seen.append(img.size) or (np.zeros((0, 4)), np.zeros(0)))
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 on display
    out = redact.redact(jpeg(Image.new("RGB", (400, 300), "white"), exif=exif))
    assert seen == [(300, 400)]
    assert Image.open(io.BytesIO(out["large"])).size == (300, 400)


class FakeResponse:
    def __init__(self, content):
        self.content = content


@pytest.fixture
def source(db, media):
    r = Response(name="T", slug="t")
    r.set_edit_key()
    r.save()
    site = Site.objects.create(response=r, name="S", slug="s")
    lyr = Layer.objects.create(site=site, name="Observations", kind="kobo")
    src = KoboSource.objects.create(layer=lyr, server_url="https://kf.kobotoolbox.org", asset_uid="a1",
                                    token_encrypted=kobo.encrypt_token("t"))
    Feature.objects.create(layer=lyr, geom=Point(1, 1, srid=4326), risa_type="water", properties={"_photos": [
        {"id": 41, "name": "p.jpg", "url": "https://kf.kobotoolbox.org/a/41?s", "large": "https://kf.kobotoolbox.org/a/41?l",
         "original": "https://kf.kobotoolbox.org/a/41"}]})
    return src


def test_photos_kept_redacted_and_fetched_once(source, monkeypatch):
    fetched = []
    monkeypatch.setattr(kobo, "attachment", lambda src, url: fetched.append(url) or FakeResponse(FACES))
    monkeypatch.setattr(redact, "find_faces", lambda img: (np.array([[10.0, 10, 60, 70]]), np.array([0.9])))
    assert kobo.redact_photos(source) == 1
    # From the original, not Kobo's resized copies
    assert fetched == ["https://kf.kobotoolbox.org/a/41"]
    lid = source.layer_id
    assert default_storage.exists(f"photos/{lid}/41.jpg") and default_storage.exists(f"photos/{lid}/41_thumb.jpg")
    assert kobo.redact_photos(source) == 0 and len(fetched) == 1
    assert kobo.photo(source, "41", "thumb")[:2] == b"\xff\xd8"


def test_endpoint_serves_only_the_redacted_copy(source, client, monkeypatch):
    lid = source.layer_id
    # Kobo down, or the model missing: a placeholder, never the original
    monkeypatch.setattr(kobo, "attachment", lambda src, url: FakeResponse(FACES))
    monkeypatch.setattr(redact, "find_faces", lambda img: (_ for _ in ()).throw(RuntimeError("no model")))
    res = client.get(f"/api/layers/{lid}/kobo/photos/41?size=large")
    assert res.status_code == 200 and res["Content-Type"] == "image/svg+xml" and res["Cache-Control"] == "no-store"
    assert not default_storage.exists(f"photos/{lid}/41.jpg")
    # Redacted when first opened, if the sync hasn't got to it
    monkeypatch.setattr(redact, "find_faces", lambda img: (np.zeros((0, 4)), np.zeros(0)))
    res = client.get(f"/api/layers/{lid}/kobo/photos/41?size=large")
    assert res["Content-Type"] == "image/jpeg" and res.content != FACES
    assert len(Image.open(io.BytesIO(res.content)).getexif()) == 0
    assert client.get(f"/api/layers/{lid}/kobo/photos/99").content.startswith(b"<svg")
    # Never as media, which has no access check
    assert client.get(f"/media/photos/{lid}/41.jpg").status_code == 404
