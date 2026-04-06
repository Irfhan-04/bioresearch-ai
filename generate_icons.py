"""
generate_icons.py — Creates the three required Chrome extension icon PNGs.

Generates solid #667eea (brand purple) squares at 16x16, 48x48, and 128x128.
Uses only Python stdlib: struct + zlib. No external dependencies.

Usage:
    python generate_icons.py
"""

import os
import struct
import zlib


def make_png(size: int, color: tuple = (102, 126, 234)) -> bytes:
    """
    Build a minimal valid PNG: solid color, RGB, no alpha.

    Args:
        size: Width and height in pixels (square)
        color: RGB tuple — defaults to #667eea (brand purple)
    """
    width = height = size

    raw = b""
    for _ in range(height):
        row = b"\x00"
        for _ in range(width):
            row += bytes(color)
        raw += row

    def chunk(name: bytes, data: bytes) -> bytes:
        payload = name + data
        return (
            struct.pack(">I", len(data))
            + payload
            + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
        )

    png_signature = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")

    return png_signature + ihdr + idat + iend


if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "chrome-extension")

    icons = [
        ("icon16.png", 16),
        ("icon48.png", 48),
        ("icon128.png", 128),
    ]

    for filename, size in icons:
        path = os.path.join(output_dir, filename)
        with open(path, "wb") as file_handle:
            file_handle.write(make_png(size))
        print(
            f"  ✅ Created {filename}  ({size}x{size} px, {os.path.getsize(path)} bytes)"
        )

    print("\nAll icons generated. You can delete generate_icons.py.")
