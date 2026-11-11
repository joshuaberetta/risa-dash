"""Shelter and building detectors: the one part of imagery analysis a model replaces.

risa/analysis.py reads the area of interest from the orthomosaic, hands it to a detector,
and stores what comes back as suggestions to review; it then groups shelters into blocks
and outlines the site, whatever the detector. A detector:

    id, label        stored on every feature it makes ("model"), shown in the dashboard
    simulated        True for stand-ins: their results are marked so everywhere
    gsd              metres per pixel it wants the image at
    available()      "" if it can run here, else why not (missing weights, packages)
    detect(rgb, valid, georef, tmp, report) -> list[Candidate]
        rgb: uint8 [h, w, 3]; valid: bool [h, w] (inside the image);
        georef: {"gt": GDAL geotransform in EPSG:3857, "tr": metres per pixel in
        Web Mercator units, "k": Web Mercator scale at the site, "path": the AOI raster};
        report(step, pct): progress for the dashboard, pct 35-75.

A candidate is a polygon in EPSG:4326 with its class ("shelter" or "building"), a
confidence 0-1, and whatever the detector wants kept with it (stats). See
docs/models.md for the contract, the training-data export and the evaluation.
"""

from dataclasses import dataclass, field

from django.contrib.gis.geos import GEOSGeometry


@dataclass
class Candidate:
    geom: GEOSGeometry          # Polygon, EPSG:4326
    cls: str                    # shelter | building
    confidence: float
    area_m2: float
    stats: dict = field(default_factory=dict)


class Detector:
    id = ""
    label = ""
    short = ""  # for tables and layer names
    simulated = False
    gsd = 0.25
    # Bigger areas are read coarser than gsd, to stay within memory
    max_pixels = 30_000_000
    description = ""

    def available(self) -> str:
        return ""

    def detect(self, rgb, valid, georef: dict, tmp: str, report) -> list[Candidate]:
        raise NotImplementedError


_REGISTRY: dict[str, Detector] = {}


def register(d: Detector) -> Detector:
    _REGISTRY[d.id] = d
    return d


def all_detectors() -> list[Detector]:
    from . import simulated  # noqa: F401  (registers itself)

    try:
        from . import models  # noqa: F401  (real models, when their packages are installed)
    except ImportError:
        pass
    return list(_REGISTRY.values())


def get(detector_id: str | None) -> Detector:
    by_id = {d.id: d for d in all_detectors()}
    from django.conf import settings

    return by_id.get(detector_id or settings.DEFAULT_DETECTOR) or by_id["simulated"]


def describe() -> list[dict]:
    return [{"id": d.id, "label": d.label, "short": d.short or d.label, "simulated": d.simulated, "description": d.description,
             "unavailable": d.available()} for d in all_detectors()]
