# -*- coding: utf-8 -*-
"""make_favicon.py —— 產生本站圖示（配色沿用字音站／韻圖站：深藍 #1a5276 + 白字）。

圖形：圓角方形深藍底 + 白色「吳」字 + 底部金線（對應站內的分詞小豎槓）。
輸出 favicon.ico（16/32/48/64）與 apple-touch-icon.png（180×180）。
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FONT_CANDIDATES = [
    r"D:\Wu\NetDisk Download\lxgw-wenkai-v1.530\lxgw-wenkai-v1.530\LXGWWenKai-Regular.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
]

SYS = (0x1A, 0x52, 0x76)       # --sys
SEP = (0xD9, 0xA4, 0x41)       # --sep
WHITE = (0xFF, 0xFF, 0xFF)


def font_at(size, path):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return None


def draw_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = max(2, int(size * 0.22))
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=SYS)

    # 底部金線（站內「分詞小豎槓」的意象）
    bar_h = max(1, int(size * 0.06))
    margin = int(size * 0.18)
    d.rounded_rectangle(
        [margin, size - margin - bar_h, size - margin, size - margin],
        radius=max(1, bar_h // 2), fill=SEP)

    ch = "吳"
    f = None
    for p in FONT_CANDIDATES:
        f = font_at(int(size * 0.56), p)
        if f:
            break
    if f is None:
        return img
    bbox = d.textbbox((0, 0), ch, font=f)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - w) / 2 - bbox[0]
    y = (size - h) / 2 - bbox[1] - size * 0.045
    d.text((x, y), ch, font=f, fill=WHITE)
    return img


def main():
    base = draw_icon(256)
    ico_sizes = [16, 32, 48, 64]
    imgs = [draw_icon(s) for s in ico_sizes]
    ico_path = os.path.join(ROOT, "favicon.ico")
    imgs[-1].save(ico_path, format="ICO",
                  sizes=[(s, s) for s in ico_sizes])
    print("wrote", ico_path, os.path.getsize(ico_path), "bytes")

    touch = draw_icon(180)
    # apple-touch-icon 不要透明底
    bg = Image.new("RGBA", touch.size, SYS)
    bg.alpha_composite(touch)
    p = os.path.join(ROOT, "apple-touch-icon.png")
    bg.convert("RGB").save(p, "PNG")
    print("wrote", p, os.path.getsize(p), "bytes")

    base.save(os.path.join(HERE, "_preview_256.png"), "PNG")


if __name__ == "__main__":
    main()
