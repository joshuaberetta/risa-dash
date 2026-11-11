#!/usr/bin/env python3
"""
End-to-end test against a running instance: the frontend and guide are served, a
response and site are created, imagery and vector are uploaded and processed, page 1
is rendered to PDF and the site exports as a GeoPackage.

Run by scripts/e2e.sh inside the production image, on a network with no internet, so
anything that needs to reach outside fails here first. Only the standard library (and
gdal_create from the image, for a small test GeoTIFF).

    python3 -I scripts/e2e.py --api http://web:8000
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_sample import LAYOUT, OBS, Api, E, N, S, W, feat, point  # noqa: E402


def get(url: str, timeout=30) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def wait(what: str, check, timeout: float):
    """Poll check() until it returns something truthy, or fail after timeout seconds."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            out = check()
        except OSError:
            out = None
        if out:
            return out
        time.sleep(2)
    sys.exit(f"FAIL: timed out waiting for {what}")


def ok(msg: str):
    print(f"ok   {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--online", action="store_true", help="skip the check that the internet is unreachable")
    args = ap.parse_args()
    base = args.api.rstrip("/")

    if not args.online:
        try:
            get("https://tiles.openfreemap.org/", timeout=5)
            sys.exit("FAIL: the internet is reachable; run this on a network with no way out (scripts/e2e.sh)")
        except OSError:
            ok("no internet")

    wait("the web app", lambda: get(f"{base}/api/config"), 180)
    config = json.loads(get(f"{base}/api/config"))
    online = [b["id"] for b in config["basemaps"] if b.get("online")]
    if online:
        sys.exit(f"FAIL: online basemaps offered with ONLINE_BASEMAPS=false: {online}")
    ok("config, no online basemaps")

    glyphs = config["glyphs"]
    if not glyphs.startswith("/"):
        sys.exit(f"FAIL: label fonts come from {glyphs}, not this instance")
    for font in {*config["fonts"]["regular"], *config["fonts"]["bold"], "Noto Sans Medium", "Noto Sans Italic"}:
        url = base + glyphs.replace("{fontstack}", urllib.parse.quote(font)).replace("{range}", "0-255")
        if len(get(url)) < 1000:
            sys.exit(f"FAIL: no label font at {url}")
    ok("label fonts served by the instance")

    if b"<div id=\"root\"" not in get(f"{base}/"):
        sys.exit("FAIL: / is not the frontend")
    if b"<html" not in get(f"{base}/guide/"):
        sys.exit("FAIL: /guide/ is not served")
    ok("frontend and guide")

    api = Api(base)
    r = api.call("POST", "/responses", {"name": "E2E test", "hazard": "Flood", "country": "HTI", "language": "en"})
    api.key = r["edit_key"]
    site = api.call("POST", f"/responses/{r['response']['slug']}/sites", {
        "name": "E2E site", "kind": "camp", "center": [(W + E) / 2, (N + S) / 2], "zoom": 17,
    })
    sid = site["id"]
    ok("response and site")

    with tempfile.TemporaryDirectory() as tmp:
        tif = os.path.join(tmp, "ortho.tif")
        subprocess.run(["gdal_create", "-of", "GTiff", "-outsize", "800", "240", "-bands", "3", "-ot", "Byte",
                        "-burn", "140", "-burn", "120", "-burn", "90", "-a_srs", "EPSG:4326",
                        "-a_ullr", str(W), str(N), str(E), str(S), tif], check=True, capture_output=True)
        lay = os.path.join(tmp, "layout.geojson")
        with open(lay, "w") as f:
            json.dump({"type": "FeatureCollection", "features": LAYOUT + [
                feat(point(x, y), type=t, status=st, label=lab) for t, x, y, st, lab in OBS]}, f)
        api.upload(sid, tif, "Test orthomosaic", "2026-01-01", "Synthetic")
        api.upload(sid, lay, "Test layout", "2026-01-01", "Fictional")

    def layers_done():
        layers = api.call("GET", f"/sites/{sid}")["layers"]
        return layers if all(lyr["status"] != "processing" for lyr in layers) else None

    layers = wait("imagery and vector processing", layers_done, 300)
    failed = [f"{lyr['name']}: {lyr.get('error', '')[:300]}" for lyr in layers if lyr["status"] != "ready"]
    if failed or len(layers) != 2:
        sys.exit(f"FAIL: layers not ready: {failed or layers}")
    ok("COG and vector layers ready")

    summary = api.call("GET", f"/sites/{sid}/summary")
    if not summary:
        sys.exit("FAIL: empty site summary")
    ok("site summary")

    p = api.call("POST", f"/sites/{sid}/products", {
        "title": "Common Operational Picture", "code": "E2E01", "page_size": "A3",
        "key_message": "End-to-end test.",
        "view": {"bounds": [W, S, E, N], "bearing": 0, "basemap": "positron",
                 "layers": [{"id": lyr["id"], "visible": True, "opacity": 1} for lyr in layers]},
    })
    ver = api.call("POST", f"/products/{p['id']}/render")

    def rendered():
        v = next(v for v in api.call("GET", f"/products/{p['id']}")["product"]["versions"] if v["n"] == ver["n"])
        return v if v["status"] in ("ready", "failed") else None

    v = wait("page 1 render", rendered, 300)
    if v["status"] != "ready":
        sys.exit(f"FAIL: page 1 render: {v['error'][:2000]}")
    pdf = get(base + v["pdf"])
    if not pdf.startswith(b"%PDF") or len(pdf) < 50_000:
        sys.exit(f"FAIL: page 1 PDF looks wrong ({len(pdf)} bytes)")
    ok(f"page 1 PDF, {len(pdf) // 1024} KB")

    gpkg = get(f"{base}/api/sites/{sid}/export.gpkg", timeout=120)
    if not gpkg.startswith(b"SQLite format 3"):
        sys.exit("FAIL: export.gpkg is not a GeoPackage")
    ok("GeoPackage export")

    t = api.call("POST", f"/responses/{r['response']['slug']}/bundles", {"imagery": True})
    t = wait("the bundle", lambda: (x := api.call("GET", f"/transfers/{t['id']}"))["status"] != "processing" and x, 300)
    if t["status"] != "ready":
        sys.exit(f"FAIL: bundle export: {t['error'][:2000]}")
    bundle = get(base + t["download"], timeout=120)
    if not bundle.startswith(b"PK"):
        sys.exit("FAIL: the bundle is not a zip")
    ok(f"bundle export, {len(bundle) // 1024} KB")

    # Back in, as the same response: an update that changes nothing
    u = api.call("POST", "/bundles/uploads", {"filename": "e2e.risa.zip", "size": len(bundle), "edit_key": api.key})
    for n in range(u["parts"]):
        api.call("PUT", f"/uploads/{u['id']}/parts/{n}", raw=bundle[n * u["chunk_size"]:(n + 1) * u["chunk_size"]])
    t = api.call("POST", f"/uploads/{u['id']}/complete")
    t = wait("the bundle import", lambda: (x := api.call("GET", f"/transfers/{t['id']}"))["status"] != "processing" and x, 300)
    if t["status"] != "ready" or t["result"]["created"] or t["result"]["layers"] != 2:
        sys.exit(f"FAIL: bundle import: {t['error'][:2000] or t['result']}")
    after = api.call("GET", f"/sites/{sid}")["layers"]
    if sorted(lyr["id"] for lyr in after) != sorted(lyr["id"] for lyr in layers):
        sys.exit("FAIL: the import changed the site's layers")
    ok("bundle import")
    print("PASS")


if __name__ == "__main__":
    main()
