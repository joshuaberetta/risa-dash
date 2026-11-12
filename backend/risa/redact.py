"""Faces hidden in Kobo photos before anyone sees them. A photo is read once from Kobo, its
faces found and smudged beyond recognition, its metadata (GPS, phone, time) dropped, and
the copy kept under photos/<layer>/ (never served as media). Only that copy leaves the
server: if a photo can't be checked, it isn't shown. Kobo keeps the original.

Faces: YuNet 2023mar (MIT), from the OpenCV model zoo, 230 KB. It reads 640x640, so a
large photo is read whole and again in overlapping tiles, for the faces far away. No
detector finds every face: one turned away, very small or in shadow can be missed, so
the SOP still asks for infrastructure, not people, in shot.
"""

import io

import numpy as np
from django.conf import settings
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .detectors.models import nms

FILE = "face-yunet-2023mar.onnx"
SIZE = 640
# Low on purpose: a smudged patch of wall costs little, a missed face a lot
MIN_SCORE = 0.5
# Tiles are read with the photo's long side at this many pixels: faces to about 12 px
TILED = 1920
LARGE, THUMB = 1600, 480
# A face is shrunk to this many pixels across
BLOCKS = 5

_session = None


def available() -> str:
    path = settings.MODELS_DIR / FILE
    return "" if path.exists() else f"no face model at {path} (scripts/fetch-models.sh)"


def _sess():
    global _session
    if _session is None:
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = settings.MODEL_THREADS
        _session = ort.InferenceSession(str(settings.MODELS_DIR / FILE), opts, providers=["CPUExecutionProvider"])
    return _session


def _read(chip: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Faces in one 640x640 RGB chip: boxes (x0, y0, x1, y1) and scores. The decoding is
    OpenCV's FaceDetectorYN: per stride, a score from class x objectness and a box from
    the cell's offset and log size."""
    x = np.ascontiguousarray(chip[:, :, ::-1].transpose(2, 0, 1)[None], dtype=np.float32)  # BGR, 0-255
    sess = _sess()
    out = dict(zip([o.name for o in sess.get_outputs()], sess.run(None, {sess.get_inputs()[0].name: x}), strict=True))
    boxes, scores = [], []
    for s in (8, 16, 32):
        n = SIZE // s
        score = np.sqrt(np.clip(out[f"cls_{s}"][0, :, 0], 0, 1) * np.clip(out[f"obj_{s}"][0, :, 0], 0, 1))
        keep = score >= MIN_SCORE
        if not keep.any():
            continue
        idx = np.nonzero(keep)[0]
        b = out[f"bbox_{s}"][0, idx]
        cx, cy = (idx % n + b[:, 0]) * s, (idx // n + b[:, 1]) * s
        w, h = np.exp(b[:, 2]) * s, np.exp(b[:, 3]) * s
        boxes.append(np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1))
        scores.append(score[idx])
    if not boxes:
        return np.zeros((0, 4)), np.zeros(0)
    return np.concatenate(boxes), np.concatenate(scores)


def _fit(img: Image.Image, long: int) -> tuple[np.ndarray, float]:
    """The photo with its long side at `long` px (never enlarged past 2x), and the scale."""
    k = min(long / max(img.size), 2.0)
    size = (max(1, round(img.width * k)), max(1, round(img.height * k)))
    return np.asarray(img.resize(size, Image.BILINEAR) if k != 1 else img), k


def find_faces(img: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    """Faces in an RGB photo, as boxes in its pixels, and their scores."""
    boxes, scores = [], []
    passes = [SIZE] + ([TILED] if max(img.size) > SIZE * 1.5 else [])
    for long in passes:
        a, k = _fit(img, long)
        H, W = a.shape[:2]
        step = SIZE - SIZE // 4
        for r0 in range(0, max(H - SIZE // 4, 1), step):
            for c0 in range(0, max(W - SIZE // 4, 1), step):
                chip = np.zeros((SIZE, SIZE, 3), np.uint8)
                part = a[r0:r0 + SIZE, c0:c0 + SIZE]
                chip[:part.shape[0], :part.shape[1]] = part
                b, s = _read(chip)
                if len(b):
                    boxes.append((b + [c0, r0, c0, r0]) / k)
                    scores.append(s)
    if not boxes:
        return np.zeros((0, 4)), np.zeros(0)
    b, s = np.concatenate(boxes), np.concatenate(scores)
    keep = nms(b, s, 0.3)
    return b[keep], s[keep]


def hide(img: Image.Image, boxes: np.ndarray) -> Image.Image:
    """Each face, with its hair and ears, smudged in an oval: shrunk to a few pixels and
    blown up again, so there's nothing left to sharpen back."""
    out = img.copy()
    for x0, y0, x1, y1 in boxes:
        w, h = x1 - x0, y1 - y0
        x0, x1 = max(0, int(x0 - w * 0.3)), min(img.width, int(x1 + w * 0.3))
        y0, y1 = max(0, int(y0 - h * 0.35)), min(img.height, int(y1 + h * 0.25))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        patch = out.crop((x0, y0, x1, y1))
        small = patch.resize((BLOCKS, max(1, round(BLOCKS * patch.height / patch.width))), Image.BOX)
        patch = small.resize(patch.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(max(2, patch.width / 12)))
        mask = Image.new("L", patch.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, patch.width - 1, patch.height - 1), fill=255)
        out.paste(patch, (x0, y0), mask.filter(ImageFilter.GaussianBlur(max(1, (x1 - x0) / 20))))
    return out


def _jpeg(img: Image.Image, long: int) -> bytes:
    img = img.copy()
    img.thumbnail((long, long), Image.LANCZOS)
    buf = io.BytesIO()
    # Without exif=, Pillow writes none: no GPS, camera, phone or time
    img.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue()


def redact(data: bytes) -> dict:
    """A photo as Kobo has it, to {"large", "thumb"} JPEGs with faces hidden and no
    metadata, and the number of faces found."""
    with Image.open(io.BytesIO(data)) as im:
        # Upright first: phones store the turn in EXIF, and the model wants faces upright
        img = ImageOps.exif_transpose(im).convert("RGB")
    boxes, _ = find_faces(img)
    img = hide(img, boxes)
    return {"large": _jpeg(img, LARGE), "thumb": _jpeg(img, THUMB), "faces": len(boxes)}
