"""The stand-in detector: colour rules on the real image (risa/analysis.py), re-scored by
the response's version learned from people's reviews (risa/learning.py), if any."""

import time

from .. import analysis
from . import Candidate, Detector, register


class Simulated(Detector):
    id = "simulated"
    label = "Simulated (colour rules)"
    simulated = True
    gsd = analysis.GSD
    description = ("A stand-in, not a model: bright grey roofs and blue tarps are shelter candidates. Its outlines "
                   "sit on real objects, so reviewing is realistic, but its counts are not reliable.")

    def __init__(self, learned=None):
        self.learned = learned  # a ready Detector row: rules and weights learned from reviews

    def for_response(self, response) -> "Simulated":
        return Simulated(analysis.latest_detector(response))

    @property
    def model_name(self) -> str:
        return self.learned.name if self.learned else analysis.MODEL

    def detect(self, rgb, valid, georef, tmp, report) -> list[Candidate]:
        report("Finding shelters and roofs", 35)
        mask = analysis.detect(rgb, valid, self.learned.params.get("rules") if self.learned else None)
        # A model takes longer; keep the simulation honest about the wait, roughly
        time.sleep(1.5)
        report("Tracing outlines", 60)
        polys = analysis.polygonise(mask, georef, tmp)
        return [Candidate(g, cls, conf, a, st) for g, cls, a, conf, st in analysis.classify(polys, georef, rgb, self.learned)]


register(Simulated())
