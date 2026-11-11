#!/bin/sh
# Map label fonts (glyph PBFs, SIL OFL), pinned and checked, into <dest>/<font name>/:
# Noto Sans Regular, Medium and Italic from Protomaps' assets (what their basemaps label
# in) and Noto Sans Bold from OpenMapTiles' (what the dashboard labels in, as OpenFreeMap).
# The image build runs it into the frontend (deploy/Dockerfile), so labels need no internet.
# For `npm run dev`:  scripts/fetch-fonts.sh frontend/public/fonts
set -eu
dest=${1:?usage: fetch-fonts.sh <dest>}
PM_COMMIT=028c18f713baecad011301ff7a69acc39bcc2ae7   # protomaps/basemaps-assets, as kobo-in-a-box's maps
PM_SHA256=57e40e8c512bd8042d0a3a251f19d0d1c8523ad963c666c3c6643bada4dc92d0
OMT_VERSION=v2.0                                     # openmaptiles/fonts
OMT_SHA256=3a7a6c2dcd940a840aa6ffac8f39758252a667a0b329945b071fb44bf00e7f47

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
get() {  # get <url> <file> <sha256>
    curl -fsSL --retry 3 -o "$2" "$1"
    [ "$(sha "$2")" = "$3" ] || { echo "fetch-fonts: $1 doesn't match its checksum" >&2; exit 1; }
}

get "https://codeload.github.com/protomaps/basemaps-assets/tar.gz/$PM_COMMIT" "$tmp/pm.tgz" "$PM_SHA256"
get "https://github.com/openmaptiles/fonts/releases/download/$OMT_VERSION/$OMT_VERSION.zip" "$tmp/omt.zip" "$OMT_SHA256"
mkdir -p "$tmp/pm" "$dest"
tar -C "$tmp/pm" -xzf "$tmp/pm.tgz" --strip-components=1
for f in "Noto Sans Regular" "Noto Sans Medium" "Noto Sans Italic"; do
    rm -rf "${dest:?}/$f" && cp -R "$tmp/pm/fonts/$f" "$dest/"
done
cp "$tmp/pm/fonts/OFL.txt" "$dest/OFL.txt"
python3 -I -c '
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    z.extractall(sys.argv[2], [n for n in z.namelist() if n.startswith("Noto Sans Bold/")])
' "$tmp/omt.zip" "$dest"
echo "fetch-fonts: $(ls "$dest" | grep -c Noto) fonts in $dest"
