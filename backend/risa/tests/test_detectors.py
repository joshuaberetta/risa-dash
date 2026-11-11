import numpy as np
import pytest

from risa import detectors
from risa.detectors import models


def test_nms_drops_overlaps_and_parts_inside():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [2, 2, 6, 6], [20, 20, 30, 30]], float)
    scores = np.array([0.9, 0.8, 0.7, 0.6])
    # The second overlaps the first; the third lies inside it; the fourth is apart
    assert models.nms(boxes, scores, 0.4) == [0, 3]


class FakeSession:
    """Stands in for ONNX Runtime: one shelter box in the middle of each 1024 tile."""

    def get_inputs(self):
        return [type("I", (), {"name": "images"})]

    def get_modelmeta(self):
        return type("M", (), {"custom_metadata_map": {"names": "{0: 'building', 9: 'shelter informal', 11: 'tent'}"}})

    def run(self, _, feeds):
        out = np.zeros((1, 4 + 15, 2), np.float32)
        out[0, :4, 0] = [512, 512, 60, 40]
        out[0, 4 + 9, 0] = 0.9      # shelter informal
        out[0, :4, 1] = [100, 100, 50, 50]
        out[0, 4 + 2, 1] = 0.95     # construction hole: not counted
        return [out]


@pytest.mark.django_db
def test_yolo_boxes_become_shelters_on_the_ground(monkeypatch):
    det = models.ShelterYolo()
    monkeypatch.setattr(det, "_session", FakeSession())
    det.classes = {0: "building", 2: "construction_hole", 9: "shelter informal", 11: "tent"}
    rgb = np.zeros((1024, 1024, 3), np.uint8)
    valid = np.ones((1024, 1024), bool)
    # 7 cm/px at the equator, origin at (0, 0) in Web Mercator
    georef = {"gt": [0, 0.07, 0, 0, 0, -0.07], "tr": 0.07, "k": 1.0, "path": ""}
    found = det.detect(rgb, valid, georef, "", lambda *a: None)
    assert len(found) == 1
    c = found[0]
    assert c.cls == "shelter" and c.confidence == 0.9 and c.stats["model_class"] == "shelter informal"
    assert c.area_m2 == pytest.approx(60 * 40 * 0.07 ** 2, rel=0.01)
    assert c.geom.srid == 4326 and c.geom.centroid.x == pytest.approx(512 * 0.07 / 111319.49, rel=0.01)


def test_detectors_listed_with_why_not():
    ids = {d["id"]: d for d in detectors.describe()}
    assert ids["simulated"]["simulated"] and ids["simulated"]["unavailable"] == ""
    assert ids["yolo-shelters"]["simulated"] is False
