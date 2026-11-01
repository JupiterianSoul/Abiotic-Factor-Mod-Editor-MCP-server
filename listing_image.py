"""mod.io listing images: 16:9, at least 512x288, under 8 MB. Standard library only."""

import struct
import zlib
from pathlib import Path

MIN_W, MIN_H = 512, 288
MAX_BYTES = 8 << 20
SIZE = (1024, 576)


def image_size(path):
    """(width, height) of a PNG or JPEG file. Raises ValueError for anything else."""
    data = Path(path).read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    raise ValueError("not a PNG or JPEG file")


def check(path):
    """Report whether an image meets mod.io's rules, with a list of problems."""
    p = Path(path)
    if not p.is_file():
        return {"ok": False, "problems": [f"No file at {p}"]}
    problems = []
    try:
        w, h = image_size(p)
    except ValueError as e:
        return {"ok": False, "problems": [str(e)]}
    if w < MIN_W or h < MIN_H:
        problems.append(f"{w}x{h} is too small: the minimum is {MIN_W}x{MIN_H}")
    if abs(w * 9 - h * 16) > max(w, h) // 50:
        problems.append(f"{w}x{h} is not 16:9")
    if p.stat().st_size >= MAX_BYTES:
        problems.append("the file is 8 MB or larger")
    return {"ok": not problems, "width": w, "height": h, "bytes": p.stat().st_size, "problems": problems}


def make(path, color=(20, 110, 110), band=(230, 240, 235)):
    """Write a plain 1024x576 placeholder PNG with a pale band across the middle."""
    w, h = SIZE
    plain = b"\x00" + bytes(color) * w
    banded = b"\x00" + bytes(band) * w
    rows = b"".join(banded if h // 3 < y < 2 * h // 3 else plain for y in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                  + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))
    return p
