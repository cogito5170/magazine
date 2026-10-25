"""Contact sheet of a replayed flow folder: every round in order, labelled."""
import glob
import os
import sys

from PIL import Image, ImageDraw

from edas.mood.variants import fnt

root = sys.argv[1]
files = sorted(glob.glob(os.path.join(root, "*", "*.png")))
tw, cols = 600, 4
rows = []
for f in files:
    im = Image.open(f).convert("RGB")
    rows.append((os.path.relpath(f, root), im.resize((tw, round(tw * im.height / im.width)))))
th = max(im.height for _, im in rows) + 34
sheet = Image.new("RGB", (cols * (tw + 20) + 20, ((len(rows) + cols - 1) // cols) * (th + 10) + 20), (245, 243, 238))
d = ImageDraw.Draw(sheet)
for i, (name, im) in enumerate(rows):
    x, y = 20 + (i % cols) * (tw + 20), 20 + (i // cols) * (th + 10)
    sheet.paste(im, (x, y))
    d.text((x, y + im.height + 6), name, font=fnt("mono", 16), fill=(40, 40, 40))
sheet.save(sys.argv[2], quality=88)
print(sys.argv[2], sheet.size)
