"""The engraving as white pixels on a transparent background.

Tracing it to SVG works but costs ~400KB, because a 1605 engraving is thousands
of separate strokes and every one becomes a path. A PNG with a soft alpha is
both far smaller and better looking small: a hairline that a hard threshold
either keeps whole or loses entirely can instead go half-transparent, so the
hatch fades into tone as the icon shrinks instead of breaking up.

  alpha = how dark the pixel is, rescaled so paper is clear and the figure's
          own lines are solid; colour is flat white throughout
  then everything outside the oval border is cut away

Run: python alpha.py
"""

from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path(__file__).parent / "epictetus-1605.png"
CX, CY, RX, RY = 378.0, 510.0, 320.0, 455.0
PAD = 6.0
# paper and lighter background ruling sit above LO and go clear; the figure's
# own strokes sit below HI and go solid. Measured off the plate.
LO, HI = 0.46, 0.24
WEB = Path(__file__).parents[2] / "web"


def ink(box, out_h):
    """White-on-clear alpha for one crop of the plate, scaled to out_h tall."""
    grey = Image.open(SRC).convert("L").crop(tuple(int(v) for v in box))
    arr = np.asarray(grey, np.float32) / 255.0
    alpha = np.clip((LO - arr) / (LO - HI), 0.0, 1.0)

    la = np.zeros(arr.shape + (2,), np.uint8)
    la[..., 0] = 255
    la[..., 1] = (alpha * 255).astype(np.uint8)
    im = Image.fromarray(la, "LA")
    return im.resize((round(out_h * im.width / im.height), out_h), Image.LANCZOS)


def oval(out_h):
    """The whole medallion, cut to its border."""
    box = (CX - RX - PAD, CY - RY - PAD, CX + RX + PAD, CY + RY + PAD)
    im = ink(box, out_h)
    a = np.asarray(im, np.uint8).copy().astype(np.float32)

    ys, xs = np.mgrid[0 : im.height, 0 : im.width]
    r = np.sqrt(((xs - im.width / 2) / (im.width / 2)) ** 2
                + ((ys - im.height / 2) / (im.height / 2)) ** 2)
    # a soft edge so the border ring does not end in a jagged step
    a[..., 1] *= np.clip((1.0 - r) / 0.012, 0.0, 1.0)
    return Image.fromarray(a.astype(np.uint8), "LA")


def main():
    # the masthead mark: the full medallion, at twice its display height
    m = oval(560)
    m.save(WEB / "public" / "epictetus.png", optimize=True)

    # the favicon: the medallion is mud at 32px, so the tab gets the head alone
    f = ink((165, 150, 585, 570), 256)
    f.save(WEB / "app" / "icon.png", optimize=True)

    print(f"medallion {m.width}x{m.height}, head {f.width}x{f.height}")


main()
