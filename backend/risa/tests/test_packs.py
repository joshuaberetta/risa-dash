import json

import pytest
from django.core.files.storage import default_storage

from risa import packs


@pytest.fixture
def fake_pmtiles(monkeypatch):
    """pmtiles extract writes a small file; nothing reaches the internet."""
    calls = []

    def run(cmd):
        calls.append(cmd)
        if cmd[1] == "extract":
            open(cmd[3], "wb").write(b"PMTiles" + b"\0" * 100)

    monkeypatch.setattr(packs, "_run", run)
    monkeypatch.setattr(packs, "newest_build", lambda: "20261111.pmtiles")
    return calls


def test_region_from_a_box():
    fc = packs.region(bbox=[-72.4, 18.5, -72.25, 18.62])
    assert fc["features"][0]["geometry"]["coordinates"][0][0] == [-72.4, 18.5]
    with pytest.raises(packs.PackError):
        packs.region(bbox=[10, 0, 5, 1])
    with pytest.raises(packs.PackError, match="ISO"):
        packs.region(countries=["Haiti"])
    with pytest.raises(packs.PackError, match="area"):
        packs.region()


def test_build_a_pack_then_load_it_elsewhere(media, fake_pmtiles, client):
    out = media / "usb"
    m = packs.build("Port-au-Prince", bbox=[-72.4, 18.5, -72.25, 18.62], maxzoom=14, out=str(out))
    extract = fake_pmtiles[0]
    assert extract[:2] == ["pmtiles", "extract"] and extract[2] == "https://build.protomaps.com/20261111.pmtiles"
    assert "--maxzoom=14" in extract and ["pmtiles", "verify"] == fake_pmtiles[1][:2]
    assert json.loads((out / "pack.json").read_text())["files"] == m["files"]
    assert not default_storage.exists("basemaps/Port-au-Prince.pmtiles")

    assert packs.load(str(out)) == ["basemaps/Port-au-Prince.pmtiles"]
    bm = client.get("/api/config").json()["basemaps"][0]
    # A path, not PUBLIC_URL: the print worker opens the app at another address
    assert bm["id"] == "pmtiles:Port-au-Prince.pmtiles" and bm["url"] == "/media/basemaps/Port-au-Prince.pmtiles"


def test_damaged_or_odd_packs_are_refused(media, fake_pmtiles):
    out = media / "usb"
    packs.build("Haiti", bbox=[-74.5, 18, -71.6, 20.1], out=str(out))
    tile = out / "basemaps" / "Haiti.pmtiles"
    tile.write_bytes(tile.read_bytes()[:-1] + b"x")
    with pytest.raises(packs.PackError, match="damaged"):
        packs.load(str(out))
    with pytest.raises(packs.PackError, match="pack.json"):
        packs.load(str(media))
    m = json.loads((out / "pack.json").read_text())
    m["files"] = {"../settings.py": {"sha256": "", "size": 0}}
    (out / "pack.json").write_text(json.dumps(m))
    with pytest.raises(packs.PackError, match="Unexpected"):
        packs.load(str(out))
    with pytest.raises(packs.PackError, match="name"):
        packs.build("../x", bbox=[0, 0, 1, 1])


def test_build_straight_into_this_instance(media, fake_pmtiles):
    packs.build("Delmas", bbox=[-72.36, 18.53, -72.29, 18.58])
    assert packs.installed() == [("Delmas.pmtiles", 107)]
