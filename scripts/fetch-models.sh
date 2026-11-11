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

echo "fetch-models: $(ls "$dest" | grep -c '\.onnx$') model(s) in $dest"
