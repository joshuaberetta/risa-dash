"""Offline content packs: the basemap of a response's area, cut out of Protomaps' daily
OpenStreetMap build while online, for an instance that will have no internet.

    pack build <name> --country VEN [--country COL] | --bbox w,s,e,n  [--out DIR]
        online: cut the area (to zoom 15) with the pmtiles CLI, which downloads only that
        area through range requests. Without --out, straight into this instance.
    pack load DIR
        offline: check and copy a pack into this instance's basemaps

A pack folder:

    pack.json                  name, area, OpenStreetMap build, zoom, SHA-256 and size per file
    basemaps/<name>.pmtiles    listed as the basemap "Offline: <name>" (Protomaps' schema)

kobo-in-a-box makes its own country map (remote/maps) and links it in, so a box needs
no pack. Same source, same cut.
"""

import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage

from . import storage

PROTOMAPS_URL = "https://build.protomaps.com"
PROTOMAPS_BUILDS = "https://build-metadata.protomaps.dev/builds.json"
GEOBOUNDARIES = "https://www.geoboundaries.org/api/current/gbOpen/{iso}/ADM0/"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,60}$")
ATTRIBUTION = "© OpenStreetMap contributors (ODbL), Protomaps"


class PackError(Exception):
    pass


def _get_json(url: str):
    # Protomaps' CDN turns away Python's default User-Agent
    req = urllib.request.Request(url, headers={"User-Agent": f"risa-dashboard pack ({settings.SOURCE_URL})"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def newest_build() -> str:
    try:
        keys = [b["key"] for b in _get_json(PROTOMAPS_BUILDS) if b["key"].endswith(".pmtiles")]
    except OSError as e:
        raise PackError(f"Can't reach Protomaps' list of builds ({e}): building a pack needs the internet") from None
    if not keys:
        raise PackError("Protomaps lists no builds")
    return max(keys)


def region(countries: list[str] | None = None, bbox: list[float] | None = None) -> dict:
    """The area to cut: the countries' outlines (geoBoundaries ADM0) or a box."""
    if bbox:
        w, s, e, n = bbox
        if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
            raise PackError("--bbox is west,south,east,north in degrees")
        ring = [[w, s], [e, s], [e, n], [w, n], [w, s]]
        return {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}]}
    features = []
    for iso in countries or []:
        if not re.fullmatch(r"[A-Z]{3}", iso):
            raise PackError(f"Not an ISO 3166 alpha-3 code: {iso}")
        try:
            meta = _get_json(GEOBOUNDARIES.format(iso=iso))
            outline = _get_json(meta["simplifiedGeometryGeoJSON"])
        except (OSError, KeyError, ValueError) as e:
            raise PackError(f"No outline for {iso} from geoBoundaries ({e})") from None
        features += [{"type": "Feature", "properties": {"iso": iso}, "geometry": f["geometry"]}
                     for f in outline["features"]]
    if not features:
        raise PackError("Give the area: --country ISO3 (repeatable) or --bbox w,s,e,n")
    return {"type": "FeatureCollection", "features": features}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise PackError("No pmtiles CLI here (it is in the RISA Dashboard image)") from None
    except subprocess.CalledProcessError as e:
        raise PackError(f"{cmd[1]} failed: {(e.stderr or e.stdout).strip()[-500:]}") from None


def build(name: str, countries: list[str] | None = None, bbox: list[float] | None = None, maxzoom: int = 15,
          out: str | None = None, source: str | None = None) -> dict:
    """Cut the area out of Protomaps' build (newest, or `source`) into a pack folder at
    `out`, or into this instance's basemaps. Returns the pack's manifest."""
    if not NAME_RE.match(name):
        raise PackError("The name: letters, digits, spaces, - _ . (it names the basemap)")
    if not 0 <= maxzoom <= 15:
        raise PackError("--maxzoom is 0 to 15")
    area = region(countries, bbox)
    src = source or f"{PROTOMAPS_URL}/{newest_build()}"
    with tempfile.TemporaryDirectory() as tmp:
        geo = os.path.join(tmp, "region.geojson")
        Path(geo).write_text(json.dumps(area))
        cut = os.path.join(tmp, f"{name}.pmtiles")
        _run(["pmtiles", "extract", src, cut, f"--region={geo}", f"--maxzoom={maxzoom}", "--download-threads=8"])
        _run(["pmtiles", "verify", cut])
        manifest = {
            "format": "risa-pack", "version": 1, "name": name, "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "countries": countries or [], "bbox": bbox, "maxzoom": maxzoom, "source": src.rsplit("/", 1)[-1],
            "attribution": ATTRIBUTION,
            "files": {f"basemaps/{name}.pmtiles": {"sha256": _sha256(cut), "size": os.path.getsize(cut)}},
        }
        if out:
            os.makedirs(os.path.join(out, "basemaps"), exist_ok=True)
            shutil.move(cut, os.path.join(out, "basemaps", f"{name}.pmtiles"))
            Path(out, "pack.json").write_text(json.dumps(manifest, indent=1))
        else:
            storage.save(f"basemaps/{name}.pmtiles", cut, public=True)
    return manifest


def load(folder: str) -> list[str]:
    """Check a pack folder against its pack.json and copy its basemaps in. Returns them."""
    try:
        manifest = json.loads(Path(folder, "pack.json").read_text())
    except FileNotFoundError:
        raise PackError(f"No pack.json in {folder}: not a pack, or a copy that was cut off") from None
    if manifest.get("format") != "risa-pack":
        raise PackError("Not a RISA Dashboard pack")
    loaded = []
    for rel, info in manifest["files"].items():
        if not re.fullmatch(r"basemaps/[^/\\]+\.pmtiles", rel) or not NAME_RE.match(rel[9:-8]):
            raise PackError(f"Unexpected file in the pack: {rel}")
        path = os.path.join(folder, rel)
        if not os.path.exists(path):
            raise PackError(f"{rel} is missing from the pack")
        if os.path.getsize(path) != info["size"] or _sha256(path) != info["sha256"]:
            raise PackError(f"{rel} is damaged (checksum does not match); copy the pack again")
        storage.save(rel, path, public=True)
        loaded.append(rel)
    return loaded


def installed() -> list[tuple[str, int]]:
    try:
        _, files = default_storage.listdir("basemaps")
    except (FileNotFoundError, NotImplementedError):
        return []
    return [(f, default_storage.size(f"basemaps/{f}")) for f in sorted(files) if f.endswith(".pmtiles")]
