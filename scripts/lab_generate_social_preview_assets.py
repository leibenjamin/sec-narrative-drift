from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = REPO_ROOT / "public"
SOCIAL_ROOT = PUBLIC_ROOT / "social"
SHARE_IMAGE_PATH = SOCIAL_ROOT / "sec-narrative-drift-lab-share-1200x630.png"
SQUARE_ICON_PATH = SOCIAL_ROOT / "sec-narrative-drift-lab-icon-512.png"
APPLE_TOUCH_ICON_PATH = PUBLIC_ROOT / "apple-touch-icon.png"

FONT_5X7: dict[str, tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00001", "00001", "00001", "00001", "10001", "10001", "01110"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in range(0, 6, 2))  # type: ignore[return-value]


class Canvas:
    def __init__(self, width: int, height: int, background: tuple[int, int, int]) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 3)
        self.fill(background)

    def fill(self, color: tuple[int, int, int]) -> None:
        r, g, b = color
        row = bytes((r, g, b)) * self.width
        for y in range(self.height):
            start = y * self.width * 3
            self.pixels[start : start + self.width * 3] = row

    def set_pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        start = (y * self.width + x) * 3
        self.pixels[start : start + 3] = bytes(color)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int]) -> None:
        if width <= 0 or height <= 0:
            return
        left = max(0, x)
        top = max(0, y)
        right = min(self.width, x + width)
        bottom = min(self.height, y + height)
        if left >= right or top >= bottom:
            return
        row = bytes(color) * (right - left)
        for row_index in range(top, bottom):
            start = (row_index * self.width + left) * 3
            self.pixels[start : start + (right - left) * 3] = row

    def stroke_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int],
        thickness: int = 1,
    ) -> None:
        self.fill_rect(x, y, width, thickness, color)
        self.fill_rect(x, y + height - thickness, width, thickness, color)
        self.fill_rect(x, y, thickness, height, color)
        self.fill_rect(x + width - thickness, y, thickness, height, color)

    def draw_char(
        self,
        x: int,
        y: int,
        char: str,
        scale: int,
        color: tuple[int, int, int],
    ) -> None:
        glyph = FONT_5X7.get(char, FONT_5X7[" "])
        for row_index, row in enumerate(glyph):
            for column_index, cell in enumerate(row):
                if cell != "1":
                    continue
                self.fill_rect(
                    x + column_index * scale,
                    y + row_index * scale,
                    scale,
                    scale,
                    color,
                )

    def draw_text(
        self,
        x: int,
        y: int,
        text: str,
        scale: int,
        color: tuple[int, int, int],
        tracking: int = 1,
    ) -> None:
        cursor_x = x
        for char in text:
            self.draw_char(cursor_x, y, char, scale, color)
            cursor_x += (5 * scale) + tracking

    def draw_gradient_bands(self, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
        for y in range(self.height):
            ratio = y / max(1, self.height - 1)
            red = round(top[0] * (1 - ratio) + bottom[0] * ratio)
            green = round(top[1] * (1 - ratio) + bottom[1] * ratio)
            blue = round(top[2] * (1 - ratio) + bottom[2] * ratio)
            self.fill_rect(0, y, self.width, 1, (red, green, blue))

    def to_png(self, path: Path) -> None:
        raw_rows = bytearray()
        row_width = self.width * 3
        for y in range(self.height):
            raw_rows.append(0)
            start = y * row_width
            raw_rows.extend(self.pixels[start : start + row_width])

        def chunk(chunk_type: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + chunk_type
                + data
                + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
            )

        png = bytearray(b"\x89PNG\r\n\x1a\n")
        png.extend(
            chunk(
                b"IHDR",
                struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0),
            )
        )
        png.extend(chunk(b"IDAT", zlib.compress(bytes(raw_rows), level=9)))
        png.extend(chunk(b"IEND", b""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)


def draw_share_image() -> None:
    canvas = Canvas(1200, 630, rgb("#07121d"))
    canvas.draw_gradient_bands(rgb("#07121d"), rgb("#10283c"))

    slate_dark = rgb("#0f2030")
    slate_line = rgb("#d7ecff")
    sky = rgb("#38bdf8")
    amber = rgb("#f59e0b")
    steel = rgb("#9fb4c8")
    soft_text = rgb("#b8d0e6")

    canvas.fill_rect(72, 58, 360, 8, slate_line)
    canvas.draw_text(72, 92, "SEC NARRATIVE DRIFT LAB", 6, slate_line, tracking=4)
    canvas.draw_text(72, 164, "THREE CASE ITEM 1A COMPARISON", 4, soft_text, tracking=3)
    canvas.draw_text(72, 220, "COMPARE FIRST", 3, sky, tracking=3)
    canvas.draw_text(340, 220, "CHECKS SECOND", 3, amber, tracking=3)
    canvas.draw_text(664, 220, "AUDIT IF NEEDED", 3, steel, tracking=3)

    card_specs = [
        (72, 304, 320, 214, sky, "NVDA", "CLEAR FIRST SIGNAL"),
        (440, 304, 320, 214, amber, "LLY", "POLICY GEOMETRY"),
        (808, 304, 320, 214, steel, "KO", "LOW DRIFT CHECK"),
    ]

    for x, y, width, height, accent, ticker, note in card_specs:
        canvas.fill_rect(x, y, width, height, slate_dark)
        canvas.stroke_rect(x, y, width, height, accent, thickness=4)
        canvas.fill_rect(x, y, width, 16, accent)
        canvas.draw_text(x + 28, y + 42, ticker, 7, slate_line, tracking=5)
        canvas.draw_text(x + 28, y + 126, note, 3, soft_text, tracking=2)
        canvas.draw_text(x + 28, y + 170, "FY 2024 TO FY 2025", 2, accent, tracking=2)

    canvas.draw_text(72, 564, "COMPACT FILING COMPARISON FOR NVDA LLY AND KO", 3, soft_text, tracking=2)
    canvas.to_png(SHARE_IMAGE_PATH)


def draw_square_icon(size: int, destination: Path) -> None:
    canvas = Canvas(size, size, rgb("#07121d"))
    canvas.draw_gradient_bands(rgb("#07121d"), rgb("#10283c"))

    slate_line = rgb("#d7ecff")
    sky = rgb("#38bdf8")
    amber = rgb("#f59e0b")
    steel = rgb("#9fb4c8")

    margin = size // 8
    rail_height = max(8, size // 32)
    card_width = size // 7
    base_y = size // 3
    card_height = size // 3
    gap = size // 14

    canvas.fill_rect(margin, margin, size - (margin * 2), rail_height, slate_line)
    canvas.fill_rect(margin, base_y, card_width, card_height, sky)
    canvas.fill_rect(margin + card_width + gap, base_y - size // 16, card_width, card_height + size // 16, amber)
    canvas.fill_rect(
        margin + (card_width + gap) * 2,
        base_y + size // 16,
        card_width,
        card_height - size // 16,
        steel,
    )
    canvas.fill_rect(margin, size - margin - rail_height, size - (margin * 2), rail_height, slate_line)

    scale = max(4, size // 64)
    text_width = (3 * 5 * scale) + (2 * scale * 2)
    text_x = (size - text_width) // 2
    text_y = size - margin - (scale * 12)
    canvas.draw_text(text_x, text_y, "SEC", scale, slate_line, tracking=scale * 2)
    canvas.to_png(destination)


def build_assets() -> None:
    draw_share_image()
    draw_square_icon(512, SQUARE_ICON_PATH)
    draw_square_icon(180, APPLE_TOUCH_ICON_PATH)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate static social preview assets.")
    return parser


def main() -> int:
    build_parser().parse_args()
    build_assets()
    print(f"share image: {SHARE_IMAGE_PATH}")
    print(f"square icon: {SQUARE_ICON_PATH}")
    print(f"apple touch icon: {APPLE_TOUCH_ICON_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
