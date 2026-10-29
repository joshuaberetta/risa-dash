#!/usr/bin/env python3
"""
Create a sample response through the API, for trying the dashboard with real imagery.

Imagery: IOM drone orthomosaic of "Aviation Camp", Port-au-Prince, Haiti (15/08/2012,
3.3 cm/px, Sensefly swinglet), CC BY 4.0, from OpenAerialMap:
https://map.openaerialmap.org (search "Aviation Camp part 1").

Everything else (routes, blocks, services and their status) is FICTIONAL, placed on
features visible in the image for testing only. It does not describe the camp.

    curl -L -o haiti-aviation-camp-1.tif \\
      https://oin-hotosm-temp.s3.us-east-1.amazonaws.com/69bbae0f57bbd74f1e80e3ad/0/69bbae0f57bbd74f1e80e3ae.tif
    python3 -I scripts/seed_sample.py --api http://localhost:8070 --imagery haiti-aviation-camp-1.tif

Only the standard library. Prints the site URL and the edit key.
"""

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request

# The orthomosaic's extent (WGS84) and the 1600 x 462 px thumbnail used to place features
W, N, E, S = -72.333428, 18.561558, -72.321144, 18.557989
TW, TH = 1600, 462


def ll(x: float, y: float) -> list[float]:
    return [round(W + x / TW * (E - W), 7), round(N - y / TH * (N - S), 7)]


def line(*pts):
    return {"type": "LineString", "coordinates": [ll(*p) for p in pts]}


def poly(*pts):
    ring = [ll(*p) for p in pts]
    return {"type": "Polygon", "coordinates": [ring + [ring[0]]]}


def point(x, y):
    return {"type": "Point", "coordinates": ll(x, y)}


def feat(geom, **props):
    return {"type": "Feature", "geometry": geom, "properties": {"note": "", **props}}


LAYOUT = [
    feat(line((110, 40), (590, 75), (1000, 115), (1400, 160), (1600, 190)), type="route", status="ok", label="R1",
         note="Airport road, open to all vehicles"),
    feat(line((60, 70), (40, 160), (20, 250), (0, 330)), type="route", status="partial", label="R2",
         note="Debris, light vehicles only"),
    feat(line((170, 200), (500, 205), (880, 212)), type="route", status="no", label="R3",
         note="Canal path flooded"),
    feat(line((1385, 180), (1390, 260), (1360, 330), (1300, 400)), type="route", status="partial", label="R4",
         note="Single lane, queues at distribution times"),
    feat(poly((120, 2), (505, 8), (505, 45), (120, 38)), type="block", label="Block A"),
    feat(poly((520, 10), (900, 12), (900, 80), (520, 70)), type="block", label="Block B"),
    feat(poly((115, 82), (555, 96), (555, 192), (115, 172)), type="block", label="Block C"),
    feat(poly((565, 98), (725, 110), (725, 196), (565, 192)), type="block", label="Block D"),
    feat(poly((890, 135), (1375, 168), (1375, 212), (890, 214)), type="block", label="Block E"),
    feat(poly((170, 196), (880, 204), (880, 222), (170, 214)), type="flood", label="Flooded canal"),
    feat(poly((742, 140), (842, 140), (842, 190), (742, 190)), type="health", status="partial", label="Health centre",
         note="Open mornings only"),
    feat(poly((1495, 335), (1582, 335), (1577, 452), (1490, 452)), type="dist", status="ok", label="Distribution site"),
]

OBS = [
    ("water", 300, 120, "ok", "WP-01"), ("water", 450, 140, "no", "WP-02"), ("water", 650, 150, "partial", "WP-03"),
    ("water", 1000, 182, "ok", "WP-04"), ("water", 1200, 192, "no", "WP-05"), ("water", 700, 40, "ok", "WP-06"),
    ("latrine", 200, 150, "partial", "LT-01"), ("latrine", 520, 170, "no", "LT-02"), ("latrine", 950, 200, "ok", "LT-03"),
    ("latrine", 1300, 198, "partial", "LT-04"), ("latrine", 800, 30, "ok", "LT-05"),
    ("hand", 330, 152, "ok", "HW-01"), ("hand", 1020, 196, "partial", "HW-02"),
    ("cfs", 880, 175, "ok", "CFS-01"), ("registration", 860, 122, "ok", "Registration"),
    ("gate", 115, 60, "ok", "West entrance"), ("gate", 1390, 172, "partial", "East entrance"),
    ("storage", 330, 262, "ok", "WH-01"), ("choke", 560, 86, "partial", "Market crossing"),
]


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.key = ""

    def call(self, method, path, body=None, raw=None, headers=None):
        h = {"Accept": "application/json", **(headers or {})}
        if self.key:
            h["X-Edit-Key"] = self.key
        data = None
        if raw is not None:
            data = raw
            h["Content-Type"] = "application/octet-stream"
        elif body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(f"{self.base}/api{path}", data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                txt = r.read().decode()
                return json.loads(txt) if txt else None
        except urllib.error.HTTPError as e:
            sys.exit(f"{method} {path}: {e.code} {e.read().decode()[:500]}")

    def upload(self, site_id, path, name, captured_at=None, attribution=""):
        size = os.path.getsize(path)
        u = self.call("POST", f"/sites/{site_id}/uploads", {
            "filename": os.path.basename(path), "size": size, "name": name,
            "captured_at": captured_at, "attribution": attribution,
        })
        with open(path, "rb") as f:
            for n in range(u["parts"]):
                self.call("PUT", f"/uploads/{u['id']}/parts/{n}", raw=f.read(u["chunk_size"]))
                print(f"\r  {name}: {n + 1}/{u['parts']} parts", end="", flush=True)
        print()
        return self.call("POST", f"/uploads/{u['id']}/complete")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://localhost:8070")
    ap.add_argument("--imagery", required=True, help="haiti-aviation-camp-1.tif")
    ap.add_argument("--create-key", default=os.environ.get("CREATE_KEY", ""))
    args = ap.parse_args()

    api = Api(args.api)
    r = api.call("POST", "/responses", {
        "name": "Sample: Port-au-Prince displacement site (test data)", "hazard": "Earthquake", "country": "HTI",
        "glide": "TEST-0000-HTI", "language": "en",
    }, headers={"X-Create-Key": args.create_key} if args.create_key else None)
    api.key = r["edit_key"]
    slug = r["response"]["slug"]
    site = api.call("POST", f"/responses/{slug}/sites", {
        "name": "Aviation Camp", "place": "Delmas, Port-au-Prince, Haiti · imagery IOM 2012, other data fictional",
        "kind": "camp", "center": [(W + E) / 2, (N + S) / 2], "zoom": 17.4,
    })
    sid = site["id"]
    print(f"Response {slug}, site {site['slug']}")

    layers = [api.upload(sid, args.imagery, "Drone orthomosaic (IOM, 2012)", "2012-08-15",
                         "IOM drone orthomosaic via OpenAerialMap, CC BY 4.0, Sensefly swinglet")]
    with tempfile.TemporaryDirectory() as tmp:
        lay = os.path.join(tmp, "site-layout-fictional.geojson")
        with open(lay, "w") as f:
            json.dump({"type": "FeatureCollection", "features": LAYOUT}, f)
        obs = os.path.join(tmp, "risa-observations-fictional.geojson")
        with open(obs, "w") as f:
            json.dump({"type": "FeatureCollection", "features": [
                feat(point(x, y), type=t, status=st, label=lab, observed="2026-10-27") for t, x, y, st, lab in OBS
            ]}, f)
        layers.append(api.upload(sid, lay, "Site layout (fictional)", "2026-10-27", "Fictional test data"))
        layers.append(api.upload(sid, obs, "RISA observations (fictional)", "2026-10-27", "Fictional KoboCollect-style observations"))

    print("Waiting for processing…", end="", flush=True)
    for _ in range(120):
        full = api.call("GET", f"/sites/{sid}")
        states = {lyr["name"]: lyr["status"] for lyr in full["layers"]}
        if all(s != "processing" for s in states.values()):
            break
        print(".", end="", flush=True)
        time.sleep(3)
    print()
    for lyr in full["layers"]:
        print(f"  {lyr['status']:10} {lyr['name']} {lyr.get('error', '')[:200]}")

    # A page 1 framed on the camp
    pad = 0.0004
    api.call("POST", f"/sites/{sid}/products", {
        "title": "Common Operational Picture", "code": "TEST01", "version_label": "Initial assessment · Day 2 · v1.0",
        "page_size": "A3", "authority": "Direction de la Protection Civile (example)",
        "key_message": "Test data. Blocks C and D border the flooded canal. Use R1 from the west or east; R3 is closed.",
        "view": {"bounds": [W + pad * 2, S - pad * 0.2, E - pad * 6, N + pad * 0.2], "bearing": 0,
                 "basemap": "positron", "layers": [{"id": lyr["id"], "visible": True, "opacity": 1} for lyr in full["layers"]]},
    })
    print(f"\nOpen  {args.api.replace(':8070', ':5173')}/r/{slug}/{site['slug']}")
    print(f"Edit key (saved nowhere else): {api.key}")


if __name__ == "__main__":
    main()
