import shutil
import subprocess
from pathlib import Path

import pytest

from risa import page1

TEMPLATE = Path(page1.__file__).parent / "typst"


def test_frames_fit_the_page():
    for size, L in page1.LAYOUT.items():
        f = page1.frames(size)
        mw, mh = f["map"]
        assert mw + L["side"] == L["w"]
        assert mh + L["band"] + L["foot"] == L["h"]
        iw, ih = f["inset"]
        assert iw < mw / 3 and ih < mh / 3
        assert f["locators"] == {"place": "map", "area": {"x": 4, "y": 4, "w": iw, "h": ih}, "overview": None,
                                 "size": [4 + iw, 4 + ih]}


def test_locator_settings_are_cleaned():
    assert page1.locators(None) == page1.DEFAULT_LOCATORS
    assert page1.locators({"country": 1, "place": "elsewhere", "x": 2}) == {"area": True, "country": True, "place": "map"}


@pytest.mark.parametrize("size", ["A3", "A4"])
@pytest.mark.parametrize("place", ["map", "side"])
def test_overview_sits_under_the_area_locator_and_fits(size, place):
    L = page1.LAYOUT[size]
    loc = page1.frames(size, {"country": True, "place": place})["locators"]
    a, o = loc["area"], loc["overview"]
    assert o["x"] == a["x"] and o["y"] == a["y"] + a["h"] + page1.LOCATOR_GAP
    assert o["w"] < a["w"]
    assert loc["size"] == [a["x"] + a["w"], o["y"] + o["h"]]
    if place == "side":
        assert loc["size"][0] == L["side"] - 2 * page1.SIDE_PAD[0]
    # Leaves most of the map, or of the side panel, for everything else
    assert loc["size"][1] < (L["h"] - L["band"] - L["foot"]) / 2
    only = page1.frames(size, {"area": False, "country": True, "place": place})["locators"]
    assert only["area"] is None and only["overview"]["y"] == a["y"]


def test_scale_bar_is_a_round_number_that_fits():
    s = page1.scale_bar(m_per_mm=2.683)
    assert s["label"] == "100 m"
    assert 0 < s["mm"] <= 40
    assert s["ratio"] == "1:2,683"
    assert page1.scale_bar(80)["label"].endswith("km")


def test_rgba_to_typst_hex():
    assert page1._hex("rgba(47,116,181,0.16)") == "#2F74B529"
    assert page1._hex("#C8A86B73") == "#C8A86B73"


@pytest.mark.parametrize("status", ["ok", "partial", "no", "unknown"])
def test_symbols_are_svg(status):
    svg = page1.symbol_svg("water", status)
    assert svg.startswith("<svg") and ">W<" in svg
    if status == "no":
        assert "<path" in svg  # the strike-through


def test_labels_have_the_same_keys():
    keys = set(page1.LABELS["en"])
    for lang, labels in page1.LABELS.items():
        assert set(labels) == keys, lang


# A blank image: Typst only needs a valid JPEG
JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c"
    "20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000"
    "000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a10823"
    "42b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778"
    "797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6"
    "e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fbd3ffd9")


@pytest.mark.skipif(not shutil.which("typst"), reason="typst not installed")
@pytest.mark.parametrize("locators", [
    {"area": False},
    {"country": True, "place": "map"},
    {"country": True, "place": "side"},
])
def test_template_compiles(tmp_path, locators):
    f = page1.frames("A4", locators)
    data = {
        "page": {**page1.LAYOUT["A4"], "inset": list(f["inset"]), "overview": list(f["page"]["overview"]), "map": list(f["map"]),
                 "side_pad": list(page1.SIDE_PAD), "locators": f["locators"]},
        "lang": "es", "labels": page1.LABELS["es"],
        "colors": {**page1.COLORS, "ink": "#1D232B", "status": {"ok": "#1F9A62", "partial": "#E9A23B", "no": "#A8281A", "unknown": "#8C939C"}},
        "draft": True, "has_inset": bool(f["locators"]["area"]), "has_overview": bool(f["locators"]["overview"]),
        "marker": [0.47, 0.45, 0.53, 0.55],
        "title": "Imagen operativa común", "subtitle": "Sitio · Lugar", "code": "MA023 · v03",
        "date": "29/10/2026 12:00", "glide": "", "authority": "", "key_message": "Mensaje",
        "glance": [{"value": "", "label": "personas", "tbc": True}],
        "legend": {"routes": ["ok", "no"], "services": [{"type": "water", "label": "Water point"}], "statuses": ["ok"],
                   "areas": [{"type": "flood", "label": "Flood", "fill": "#2F74B529", "stroke": "#2F74B5"}]},
        "sources": "Prueba.", "disclaimer": "Descargo.", "credits": "Kobo", "url": "https://example.org/r/x/y",
        "bearing": 12, "scale": page1.scale_bar(3),
    }
    page1.write_assets(tmp_path, data)
    shutil.copy(TEMPLATE / "page1.typ", tmp_path / "page1.typ")
    for name in ("map.jpg", "inset.jpg", "overview.jpg"):
        (tmp_path / name).write_bytes(JPEG)
    out = tmp_path / "out.pdf"
    p = subprocess.run(["typst", "compile", "--root", str(tmp_path), "--font-path", str(TEMPLATE / "fonts"),
                        "--ignore-system-fonts", str(tmp_path / "page1.typ"), str(out)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert out.read_bytes()[:4] == b"%PDF"
