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

# Noto Serif KR (SIL OFL 1.1) for the soft-dandy final; edas.mood.contemporary falls back to Caladea without it.
DEST2="${HOME}/.local/share/fonts/notoserifkr"
TMP2="$(mktemp -d)"
curl -sSfL -o "$TMP2/n.zip" https://github.com/notofonts/noto-cjk/releases/download/Serif2.003/13_NotoSerifKR.zip
mkdir -p "$DEST2"
for w in ExtraLight Light Regular Medium SemiBold; do
  unzip -o -q -j "$TMP2/n.zip" "SubsetOTF/KR/NotoSerifKR-$w.otf" -d "$DEST2"
done
unzip -o -q -j "$TMP2/n.zip" LICENSE -d "$DEST2"
rm -rf "$TMP2"
echo "Noto Serif KR installed to $DEST2"
