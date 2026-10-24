#!/usr/bin/env sh
# Fetch Pretendard (SIL OFL 1.1) for the final MATCH series; edas.mood.final falls back to WenQuanYi without it.
set -e
DEST="${HOME}/.local/share/fonts/pretendard"
TMP="$(mktemp -d)"
curl -sSfL -o "$TMP/p.zip" https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip
mkdir -p "$DEST"
unzip -o -q -j "$TMP/p.zip" 'public/static/Pretendard-*.otf' LICENSE.txt -d "$DEST"
rm -rf "$TMP"
echo "Pretendard installed to $DEST"
