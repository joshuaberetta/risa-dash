#!/bin/sh
# Model weights for imagery analysis (risa/detectors/models.py), pinned and checked,
# into <dest> (MODELS_DIR). The image build runs it (deploy/Dockerfile); an offline box
# gets the folder from its content pack.
set -eu
dest=${1:?usage: fetch-models.sh <dest>}
mkdir -p "$dest"
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
get() {  # get <url> <file> <sha256>
    if [ -f "$dest/$2" ] && [ "$(sha "$dest/$2")" = "$3" ]; then return; fi
    curl -fsSL --retry 3 -o "$dest/$2.part" "$1"
    [ "$(sha "$dest/$2.part")" = "$3" ] || { echo "fetch-models: $1 doesn't match its checksum" >&2; exit 1; }
    mv "$dest/$2.part" "$dest/$2"
}

# Shelters in camps, YOLOv8n (MIT; trained with Ultralytics, AGPL-3.0)
# github.com/alex6H/RefugeeCampShelterDetection-YOLOv8
SHELTERS=e91bd16e6060555bee8e21f1f9af3bfa496d7d33
get "https://github.com/alex6H/RefugeeCampShelterDetection-YOLOv8/raw/$SHELTERS/best.onnx" \
    refugee-shelters-yolov8n.onnx bfbe08321064479587c7825f5d125895113b3e92ab7c213f16c0bd222830fd41
# Its licence, from the same commit
curl -fsSL --retry 3 -o "$dest/refugee-shelters-yolov8n.LICENSE" \
    "https://raw.githubusercontent.com/alex6H/RefugeeCampShelterDetection-YOLOv8/$SHELTERS/LICENSE"

# Faces in Kobo photos, YuNet 2023mar (MIT), from the OpenCV model zoo (risa/redact.py)
YUNET=f12e12798e8314f7c074a6656816c048dcc95b7a
get "https://github.com/opencv/opencv_zoo/raw/$YUNET/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" \
    face-yunet-2023mar.onnx 8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4
curl -fsSL --retry 3 -o "$dest/face-yunet-2023mar.LICENSE" \
    "https://raw.githubusercontent.com/opencv/opencv_zoo/$YUNET/models/face_detection_yunet/LICENSE"

echo "fetch-models: $(ls "$dest" | grep -c '\.onnx$') model(s) in $dest"
