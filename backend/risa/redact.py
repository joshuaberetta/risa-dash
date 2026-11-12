"""Faces and people hidden in Kobo photos before anyone sees them. A photo is read once
from Kobo, its faces and people found and smudged beyond recognition, its metadata (GPS,
phone, time) dropped, and the copy kept under photos/<layer>/ (never served as media).
Only that copy leaves the server: if a photo can't be checked, it isn't shown. Kobo
keeps the original.

Two models, both reading 640x640, so a large photo is read whole and again in
overlapping tiles, for what's far away:
- faces: YuNet 2023mar (MIT), from the OpenCV model zoo, 230 KB. Faces turned to the
  camera, to about 20 px;
- people: YOLOX-s on COCO (Apache-2.0), Megvii's own export, 35 MB. For wide shots of a
  camp, where faces are too small, turned away or in profile: a person whose face
  wasn't found is smudged whole, as clothes can tell who someone is too (see unseen()).
No detector finds everyone: someone half hidden, in a doorway or very far away can be
missed, so the SOP still asks for infrastructure, not people, in shot.
"""

import io

import numpy as np
from django.conf import settings
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .detectors.models import nms

SIZE = 640
# Tiles are read with the photo's long side at this many pixels
TILED = 1920
LARGE, THUMB = 1600, 480
# A face is shrunk to this many pixels across, a person too
BLOCKS = 5
# A person this tall (of the photo's height) with no face found has only the top of their box hidden
LARGE_PERSON = 0.3


class Model:
    def __init__(self, file: str, pad: int, min_score: float):
        self.file, self.pad, self.min_score = file, pad, min_score
        self._session = None

    @property
    def path(self):
        return settings.MODELS_DIR / self.file

    def session(self):
        if self._session is None:
            import onnxruntime as ort

            opts = ort.SessionOptions()
            opts.intra_op_num_threads = settings.MODEL_THREADS
            self._session = ort.InferenceSession(str(self.path), opts, providers=["CPUExecutionProvider"])
        return self._session

    def run(self, chip: np.ndarray) -> dict:
        x = np.ascontiguousarray(chip[:, :, ::-1].transpose(2, 0, 1)[None], dtype=np.float32)  # BGR, 0-255
        sess = self.session()
        return dict(zip([o.name for o in sess.get_outputs()], sess.run(None, {sess.get_inputs()[0].name: x}), strict=True))


# Low on purpose: a smudged patch of wall costs little, a missed face a lot
FACES = Model("face-yunet-2023mar.onnx", pad=0, min_score=0.5)
# YOLOX pads with grey, as it was trained
PEOPLE = Model("people-yolox-s.onnx", pad=114, min_score=0.3)


def available() -> str:
    missing = [str(m.path) for m in (FACES, PEOPLE) if not m.path.exists()]
    return f"no model at {', '.join(missing)} (scripts/fetch-models.sh)" if missing else ""


def _faces_in(chip: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Faces in one 640x640 RGB chip: boxes (x0, y0, x1, y1) and scores. The decoding is
    OpenCV's FaceDetectorYN: per stride, a score from class x objectness and a box from
    the cell's offset and log size."""
    out = FACES.run(chip)
    boxes, scores = [], []
    for s in (8, 16, 32):
        n = SIZE // s
        score = np.sqrt(np.clip(out[f"cls_{s}"][0, :, 0], 0, 1) * np.clip(out[f"obj_{s}"][0, :, 0], 0, 1))
        idx = np.nonzero(score >= FACES.min_score)[0]
        b = out[f"bbox_{s}"][0, idx]
        cx, cy = (idx % n + b[:, 0]) * s, (idx // n + b[:, 1]) * s
        w, h = np.exp(b[:, 2]) * s, np.exp(b[:, 3]) * s
        boxes.append(np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1))
        scores.append(score[idx])
    return np.concatenate(boxes), np.concatenate(scores)


def _grid() -> tuple[np.ndarray, np.ndarray]:
    cells, strides = [], []
    for s in (8, 16, 32):
        n = SIZE // s
        yy, xx = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
        cells.append(np.stack([xx, yy], -1).reshape(-1, 2))
        strides.append(np.full((n * n, 1), s))
    return np.concatenate(cells), np.concatenate(strides)


GRID = _grid()


def _people_in(chip: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """People in one chip. YOLOX: per cell, a box from the cell's offset and log size, and
    a score from objectness x the class (COCO's first, person)."""
    out = next(iter(PEOPLE.run(chip).values()))[0]
    cells, strides = GRID
    xy, wh = (out[:, :2] + cells) * strides, np.exp(out[:, 2:4]) * strides
    score = out[:, 4] * out[:, 5]
    keep = score >= PEOPLE.min_score
    return np.concatenate([xy - wh / 2, xy + wh / 2], axis=1)[keep], score[keep]


def _tiled(img: Image.Image, model: Model, read, iou: float) -> tuple[np.ndarray, np.ndarray]:
    """What `read` finds in an RGB photo, read whole and, if large, in tiles; as boxes in
    the photo's pixels, and their scores."""
    boxes, scores = [], []
    for long in [SIZE] + ([TILED] if max(img.size) > SIZE * 1.5 else []):
        # Never enlarged past 2x
        k = min(long / max(img.size), 2.0)
        size = (max(1, round(img.width * k)), max(1, round(img.height * k)))
        a = np.asarray(img.resize(size, Image.BILINEAR) if k != 1 else img)
        H, W = a.shape[:2]
        step = SIZE - SIZE // 4
        for r0 in range(0, max(H - SIZE // 4, 1), step):
            for c0 in range(0, max(W - SIZE // 4, 1), step):
                chip = np.full((SIZE, SIZE, 3), model.pad, np.uint8)
                part = a[r0:r0 + SIZE, c0:c0 + SIZE]
                chip[:part.shape[0], :part.shape[1]] = part
                b, s = read(chip)
                boxes.append((b + [c0, r0, c0, r0]) / k)
                scores.append(s)
    b, s = np.concatenate(boxes), np.concatenate(scores)
    if not len(b):
        return np.zeros((0, 4)), np.zeros(0)
    keep = nms(b, s, iou)
    return b[keep], s[keep]


def find_faces(img: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    return _tiled(img, FACES, _faces_in, 0.3)


def find_people(img: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    return _tiled(img, PEOPLE, _people_in, 0.45)


def hide(img: Image.Image, boxes: np.ndarray, grow: tuple[float, float, float], oval: bool) -> Image.Image:
    """Each box, grown by (sides, top, bottom) of its size, smudged: shrunk to a few
    pixels across and blown up again, so there's nothing left to sharpen back. Faces in
    an oval, people in a soft-cornered box."""
    out = img.copy()
    sides, top, bottom = grow
    for x0, y0, x1, y1 in boxes:
        w, h = x1 - x0, y1 - y0
        x0, x1 = max(0, int(x0 - w * sides)), min(img.width, int(x1 + w * sides))
        y0, y1 = max(0, int(y0 - h * top)), min(img.height, int(y1 + h * bottom))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        patch = out.crop((x0, y0, x1, y1))
        small = patch.resize((BLOCKS, max(1, round(BLOCKS * patch.height / patch.width))), Image.BOX)
        patch = small.resize(patch.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(max(2, patch.width / 12)))
        mask = Image.new("L", patch.size, 0)
        draw = ImageDraw.Draw(mask)
        shape = (0, 0, patch.width - 1, patch.height - 1)
        if oval:
            draw.ellipse(shape, fill=255)
        else:
            draw.rounded_rectangle(shape, radius=patch.width // 4, fill=255)
        out.paste(patch, (x0, y0), mask.filter(ImageFilter.GaussianBlur(max(1, patch.width / 20))))
    return out


def _jpeg(img: Image.Image, long: int) -> bytes:
    img = img.copy()
    img.thumbnail((long, long), Image.LANCZOS)
    buf = io.BytesIO()
    # Without exif=, Pillow writes none: no GPS, camera, phone or time
    img.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue()


def unseen(people: np.ndarray, faces: np.ndarray, height: int) -> tuple[np.ndarray, np.ndarray]:
    """People whose face wasn't found (turned away, in profile, too small), to hide whole,
    or, if they fill much of the photo, from the head to about the waist. Someone whose
    face was found keeps the rest, so a close-up of a water point with a child at it still
    shows the water point. A face is theirs only if it's where a head would be, the top of
    their box, and a head's size: not a hand, or the face of someone behind them."""
    if not len(people):
        return people, people
    if len(faces):
        cx, cy = (faces[:, 0] + faces[:, 2]) / 2, (faces[:, 1] + faces[:, 3]) / 2
        fw = faces[:, 2] - faces[:, 0]
        px0, py0, px1, py1 = (people[:, i:i + 1] for i in range(4))
        pw, ph = px1 - px0, py1 - py0
        seen = ((cx[None] > px0) & (cx[None] < px1) & (cy[None] > py0) & (cy[None] < py0 + 0.3 * ph)
                & (fw[None] > 0.1 * pw) & (fw[None] < 0.7 * pw)).any(axis=1)
        people = people[~seen]
    large = people[:, 3] - people[:, 1] > LARGE_PERSON * height
    tops = people[large].copy()
    tops[:, 3] = tops[:, 1] + (tops[:, 3] - tops[:, 1]) * 0.4
    return people[~large], tops


def redact(data: bytes) -> dict:
    """A photo as Kobo has it, to {"large", "thumb"} JPEGs with faces and people hidden
    and no metadata, and the number of each found."""
    with Image.open(io.BytesIO(data)) as im:
        # Upright first: phones store the turn in EXIF, and the models want people upright
        img = ImageOps.exif_transpose(im).convert("RGB")
    faces, _ = find_faces(img)
    people, _ = find_people(img)
    whole, tops = unseen(people, faces, img.height)
    # A person with a little room around; a face with its hair and ears
    img = hide(img, np.concatenate([whole, tops]), (0.08, 0.05, 0.03), oval=False)
    img = hide(img, faces, (0.3, 0.35, 0.25), oval=True)
    return {"large": _jpeg(img, LARGE), "thumb": _jpeg(img, THUMB), "faces": len(faces), "people": len(whole) + len(tops)}
