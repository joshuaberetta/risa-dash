"""Real models (risa/detectors/__init__.py has the contract). Weights live in MODELS_DIR:
fetched by the image build (scripts/fetch-models.sh), or copied in for an offline box.

Shelter detector: YOLOv8n fine-tuned on drone imagery of camps in DRC (around Goma),
Chad and Mozambique, by Alexis H., github.com/alex6H/RefugeeCampShelterDetection-YOLOv8
(MIT; trained with Ultralytics, AGPL-3.0). Boxes with 15 classes, at 2-10 cm/px. It's
strongest on informal shelters of wood and plastic sheeting, which most of its training
data is. Its boxes become the outlines here, axis-aligned rectangles; a segmenter
(e.g. SAM prompted with the boxes) would trace them.
"""

import numpy as np
import onnxruntime as ort
from django.conf import settings
from django.contrib.gis.geos import Polygon

from . import Candidate, Detector, register

# The model's classes, by what RISA counts. The rest (cars, latrines, tanks, water
# sources, umbrellas, holes) are dropped for now; latrines and water sources are services
# a later version could check against the Kobo observations.
SHELTER = {"dwelling", "hut", "shelter formal", "shelter informal", "tent"}
BUILDING = {"building"}


def nms(boxes: np.ndarray, scores: np.ndarray, iou: float, contain: float = 0.6) -> list[int]:
    """Greedy non-maximum suppression; boxes as x0, y0, x1, y1. A box goes if it overlaps a
    more confident one by IoU >= iou, or lies mostly (>= contain of its area) inside it:
    across tile edges the model often returns a roof whole and again in part."""
    order = scores.argsort()[::-1]
    area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    keep = []
    while order.size:
        i = order[0]
        keep.append(int(i))
        rest = order[1:]
        xx0 = np.maximum(boxes[i, 0], boxes[rest, 0])
        yy0 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx1 = np.minimum(boxes[i, 2], boxes[rest, 2])
        yy1 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(xx1 - xx0, 0, None) * np.clip(yy1 - yy0, 0, None)
        over = inter / (area[i] + area[rest] - inter + 1e-9)
        inside = inter / (np.minimum(area[i], area[rest]) + 1e-9)
        order = rest[(over < iou) & (inside < contain)]
    return keep


class ShelterYolo(Detector):
    id = "yolo-shelters"
    label = "Shelter detector (YOLOv8n, camps in DRC, Chad, Mozambique)"
    simulated = False
    # 9 cm and a low floor did best on the Haiti reference chips (of 5, 7, 9 cm; 0.05, 0.15):
    # the confidence is kept on each shelter, and the review and evaluation choose the cut
    gsd = 0.09
    # About 0.5 km² at 9 cm; larger areas are read coarser, and the model degrades past 10 cm
    max_pixels = 70_000_000
    description = ("A YOLOv8 nano model fine-tuned on drone imagery of camps around Goma, in Chad and in Mozambique "
                   "(github.com/alex6H/RefugeeCampShelterDetection-YOLOv8, MIT). Finds shelters, tents, huts and "
                   "buildings as boxes. Strongest on plastic-sheeting shelters; needs imagery at 10 cm/px or finer.")
    file = "refugee-shelters-yolov8n.onnx"
    tile, overlap, min_conf, iou = 1024, 192, 0.05, 0.4

    def __init__(self):
        self._session = None
        self.classes: dict[int, str] = {}

    @property
    def path(self):
        return settings.MODELS_DIR / self.file

    def available(self) -> str:
        return "" if self.path.exists() else f"no weights at {self.path} (scripts/fetch-models.sh)"

    def session(self) -> ort.InferenceSession:
        if not self._session:
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = settings.MODEL_THREADS  # 0: all cores
            self._session = ort.InferenceSession(str(self.path), opts, providers=["CPUExecutionProvider"])
            names = self._session.get_modelmeta().custom_metadata_map.get("names", "{}")
            self.classes = {int(k): v.strip().strip("'\"") for k, v in
                            (x.split(":", 1) for x in names.strip("{}").split(",") if ":" in x)}
        return self._session

    def detect(self, rgb, valid, georef, tmp, report) -> list[Candidate]:
        sess = self.session()
        inp = sess.get_inputs()[0].name
        H, W = rgb.shape[:2]
        T, step = self.tile, self.tile - self.overlap
        rows = list(range(0, max(H - self.overlap, 1), step))
        cols = list(range(0, max(W - self.overlap, 1), step))
        boxes, scores, labels = [], [], []
        done, total = 0, len(rows) * len(cols)
        for r0 in rows:
            for c0 in cols:
                done += 1
                if not valid[r0:r0 + T, c0:c0 + T].any():
                    continue
                chip = np.zeros((T, T, 3), np.uint8)
                part = rgb[r0:r0 + T, c0:c0 + T]
                chip[:part.shape[0], :part.shape[1]] = part
                x = np.ascontiguousarray(chip.transpose(2, 0, 1)[None], dtype=np.float32) / 255.0
                out = sess.run(None, {inp: x})[0][0]          # (4 + classes, anchors)
                cls_scores = out[4:]
                best = cls_scores.argmax(axis=0)
                conf = cls_scores.max(axis=0)
                keep = conf >= self.min_conf
                cx, cy, w, h = out[0, keep], out[1, keep], out[2, keep], out[3, keep]
                boxes.append(np.stack([cx - w / 2 + c0, cy - h / 2 + r0, cx + w / 2 + c0, cy + h / 2 + r0], axis=1))
                scores.append(conf[keep])
                labels.append(best[keep])
                if done % 10 == 0:
                    report(f"Finding shelters ({done} of {total} tiles)", 35 + int(35 * done / total))
        if not boxes:
            return []
        boxes, scores, labels = np.concatenate(boxes), np.concatenate(scores), np.concatenate(labels)
        names = np.array([self.classes.get(int(i), str(i)) for i in labels])
        group = np.where(np.isin(names, list(SHELTER)), "shelter", np.where(np.isin(names, list(BUILDING)), "building", ""))
        # Across tile edges and between the model's own classes: one box per object
        out: list[Candidate] = []
        gt, k = georef["gt"], georef["k"]
        for cls in ("shelter", "building"):
            idx = np.where(group == cls)[0]
            for i in (idx[j] for j in nms(boxes[idx], scores[idx], self.iou)):
                x0, y0, x1, y1 = np.clip(boxes[i], 0, [W, H, W, H])
                cx, cy = int((x0 + x1) / 2), int((y0 + y1) / 2)
                if x1 - x0 < 2 or y1 - y0 < 2 or not valid[min(cy, H - 1), min(cx, W - 1)]:
                    continue
                X0, X1 = gt[0] + x0 * gt[1], gt[0] + x1 * gt[1]
                Y0, Y1 = gt[3] + y1 * gt[5], gt[3] + y0 * gt[5]
                poly = Polygon.from_bbox((X0, Y0, X1, Y1))
                poly.srid = 3857
                area = (X1 - X0) * (Y1 - Y0) / k ** 2
                out.append(Candidate(poly.transform(4326, clone=True), cls, round(float(scores[i]), 3), round(area, 1),
                                     {"model_class": str(names[i]), "box_px": [round(float(v), 1) for v in (x0, y0, x1, y1)],
                                      "gsd_m": round(georef["tr"] / k, 3)}))
        report("Tracing outlines", 72)
        return out


register(ShelterYolo())
