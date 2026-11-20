#!/usr/bin/env python3
"""Render one editorial front page as a PNG, using nothing but the stdlib.

The image summarises the world news of Friday, 20 November 2026. Every pixel
is produced by the small canvas class below: an RGB byte buffer, a 5x7 bitmap
font kept in this file as bit patterns, and a hand-rolled PNG encoder that
writes IHDR / IDAT / IEND chunks around zlib-compressed scanlines.

No randomness, no clock reads, no hash-order dependence: the same input always
gives the same bytes, which is the whole point of the --check mode.
"""

import json
import os
import struct
import sys
import zlib

WIDTH = 1600
HEIGHT = 2600
SCALE = 2

INK = (24, 22, 20)
PAPER = (247, 243, 232)
RULE = (24, 22, 20)
SOFT = (120, 112, 102)
BAND_FILL = (232, 224, 208)
BAND_ACCENT = (180, 40, 30)

# ---------------------------------------------------------------------------
# font: 7 rows per glyph, 5 bits used (bit 4 is the leftmost column)
# ---------------------------------------------------------------------------

GLYPHS = {
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b11111),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "0": (0b01110, 0b10011, 0b10101, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),
    "3": (0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    ".": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b01100),
    ",": (0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b01100, 0b00100),
    ":": (0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b01100, 0b00000),
    "-": (0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000),
    "/": (0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    "(": (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "%": (0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    "'": (0b00100, 0b00100, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
}

DOT = (0b00000, 0b01110, 0b01110, 0b01110, 0b00000, 0b00000, 0b00000)

GLYPH_ADVANCE = 6   # 5 columns of ink + 1 column of tracking
LINE_HEIGHT = 9     # 7 rows of ink + 2 rows of leading


def all_glyphs():
    table = dict(GLYPHS)
    table["\u00b7"] = DOT
    return table


class Canvas:
    """A fixed RGB raster with a handful of drawing primitives."""

    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.background = background
        self.pixels = bytearray(bytes(background) * (width * height))
        self.glyphs = all_glyphs()
        self.ink_bottom = -1

    def put(self, x, y, colour):
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        i = (y * self.width + x) * 3
        self.pixels[i] = colour[0]
        self.pixels[i + 1] = colour[1]
        self.pixels[i + 2] = colour[2]
        if y > self.ink_bottom:
            self.ink_bottom = y

    def rect(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(colour) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.width + x0) * 3
            self.pixels[i:i + len(row)] = row
        if y1 - 1 > self.ink_bottom:
            self.ink_bottom = y1 - 1

    def hline(self, x, y, w, thickness=1, colour=RULE):
        self.rect(x, y, w, thickness, colour)

    def text_width(self, s, scale=1):
        if not s:
            return 0
        return (len(s) * GLYPH_ADVANCE - 1) * scale

    def text(self, s, x, y, colour=INK, scale=1):
        s = s.upper()
        cursor = x
        for ch in s:
            rows = self.glyphs.get(ch)
            if rows is not None:
                for r, bits in enumerate(rows):
                    if bits == 0:
                        continue
                    for c in range(5):
                        if bits & (1 << (4 - c)):
                            if scale == 1:
                                self.put(cursor + c, y + r, colour)
                            else:
                                self.rect(cursor + c * scale, y + r * scale,
                                          scale, scale, colour)
            cursor += GLYPH_ADVANCE * scale

    def text_right(self, s, right, y, colour=INK, scale=1):
        self.text(s, right - self.text_width(s, scale), y, colour, scale)

    def text_center(self, s, cx, y, colour=INK, scale=1):
        self.text(s, cx - self.text_width(s, scale) // 2, y, colour, scale)

    def wrap(self, s, max_width, scale=1):
        """Greedy word wrap on spaces. Words longer than the line are kept whole."""
        limit = max_width // (GLYPH_ADVANCE * scale) + 1
        lines = []
        current = ""
        for word in s.upper().split():
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= limit:
                current = current + " " + word
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def wrap_clip(self, s, max_width, max_lines, scale=1):
        lines = self.wrap(s, max_width, scale)
        if len(lines) <= max_lines:
            return lines
        kept = lines[:max_lines]
        tail = kept[-1]
        while tail and self.text_width(tail + " ...", scale) > max_width:
            cut = tail.rfind(" ")
            tail = tail[:cut] if cut > 0 else tail[:-1]
        kept[-1] = (tail + " ...").strip()
        return kept

    def png_bytes(self):
        raw = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            raw.append(0)  # filter type 0, None
            start = y * stride
            raw += self.pixels[start:start + stride]
        def chunk(tag, payload):
            body = tag + payload
            return (struct.pack(">I", len(payload)) + body
                    + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))
        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", header)
                + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                + chunk(b"IEND", b""))

    def crop(self, margin):
        if self.ink_bottom < 0:
            return Canvas(self.width, 1, self.background)
        tall = min(self.height, self.ink_bottom + 1 + margin)
        out = Canvas(self.width, tall, self.background)
        stride = self.width * 3
        out.pixels = bytearray(self.pixels[:stride * tall])
        out.ink_bottom = tall - 1
        return out


def load_fixture(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def compose(doc):
    left = 80
    right = WIDTH - 80
    column = right - left
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    stories = doc["stories"]
    by_lede = [s for s in stories if s.get("lede")]
    lede = by_lede[0] if by_lede else stories[0]
    rest = [s for s in stories if s is not lede]

    y = 56

    # masthead rules
    cv.hline(left, y, column, 2)
    y += 14
    cv.text_center(doc.get("masthead", "THE WORLD IN ONE IMAGE"),
                   WIDTH // 2, y, INK, 3)
    y += 7 * 3 + 14
    cv.text_center("AN EDITORIAL SUMMARY OF THE DAY'S GLOBAL NEWS", WIDTH // 2, y, SOFT, 1)
    y += LINE_HEIGHT + 10
    cv.hline(left, y, column, 3)
    y += 12

    # dateline row
    cv.text(doc["dateline"], left, y, INK)
    cv.text_right("EDITION " + doc["edition"] + "  /  ISSUE " + doc["issue"],
                  right, y, INK)
    y += LINE_HEIGHT + 8
    cv.hline(left, y, column, 1, SOFT)
    y += 26

    # lede story
    cv.rect(left, y + 1, 10, LINE_HEIGHT, BAND_ACCENT)
    cv.text(lede["kicker"], left + 20, y, BAND_ACCENT)
    y += LINE_HEIGHT + 18
    cv.text(lede["headline"], left, y, INK, SCALE)
    y += 7 * SCALE + 22
    for line in cv.wrap_clip(lede["summary"], column, 4, 1):
        cv.text(line, left, y, INK)
        y += LINE_HEIGHT + 3
    y += 8
    cv.text("SOURCES: " + "; ".join(lede["sources"]), left, y, SOFT)
    y += LINE_HEIGHT + 22

    cv.hline(left, y, column, 1, SOFT)
    y += 24

    # proportional bar
    cv.text("THE DAY IN PROPORTION - WEIGHT OF COVERAGE", left, y, SOFT)
    y += LINE_HEIGHT + 10
    total = sum(float(s["weight"]) for s in stories)
    bar_y = y
    bar_h = 54
    gap = 2
    usable = column - gap
    running = 0.0
    prev_edge = float(left)
    for index, story in enumerate(stories):
        running += float(story["weight"])
        edge = float(left) + usable * (running / total)
        x0 = int(round(prev_edge))
        x1 = int(round(edge))
        if index == len(stories) - 1:
            x1 = right
        cv.rect(x0, bar_y, x1 - x0, bar_h, BAND_FILL)
        cv.rect(x0, bar_y, x1 - x0, 4, BAND_ACCENT)
        share = int(round(float(story["weight"]) / total * 100))
        label = str(index + 1) + " - " + str(share) + "%"
        if x1 - x0 >= cv.text_width(label) + 12:
            cv.text(label, x0 + 6, bar_y + 16, INK)
        prev_edge = edge
    y = bar_y + bar_h + 14
    cv.text("TOTAL WEIGHT " + str(int(total)) + " ACROSS " + str(len(stories)) + " STORIES",
            left, y, SOFT)
    y += LINE_HEIGHT + 22
    cv.hline(left, y, column, 1, SOFT)
    y += 24

    # numbered list
    cv.text("ALSO TODAY", left, y, SOFT)
    y += LINE_HEIGHT + 14
    for index, story in enumerate(rest, start=1):
        num = str(index) + "."
        cv.text(num, left, y, BAND_ACCENT)
        cv.text(story["kicker"], left + 40, y, SOFT)
        y += LINE_HEIGHT + 4
        cv.text(story["headline"], left + 40, y, INK)
        y += LINE_HEIGHT + 6
        for line in cv.wrap_clip(story["summary"], column - 40, 3, 1):
            cv.text(line, left + 40, y, INK)
            y += LINE_HEIGHT + 2
        cv.text("SOURCES: " + "; ".join(story["sources"]), left + 40, y, SOFT)
        y += LINE_HEIGHT + 18
        if index < len(rest):
            cv.hline(left, y, column, 1, BAND_FILL)
            y += 16

    # wire strip
    y += 6
    cv.hline(left, y, column, 2)
    y += 12
    cv.text("WIRE", left, y, BAND_ACCENT)
    cv.text("THREE LINE ITEMS FROM THE OVERNIGHT FILE", left + 60, y, SOFT)
    y += LINE_HEIGHT + 8
    for item in doc["wire"]:
        lines = cv.wrap_clip("- " + item, column - 12, 2, 1)
        for line in lines:
            cv.text(line, left + 12, y, INK)
            y += LINE_HEIGHT + 3
        y += 6
    y += 8
    cv.hline(left, y, column, 2)
    y += 12
    cv.text("SOURCES: REPORTS FROM THE WIRE AS WRITTEN FOR THIS EDITION",
            left, y, SOFT)
    cv.text_right("DETERMINISTIC BY CONSTRUCTION", right, y, SOFT)
    y += LINE_HEIGHT + 4
    cv.text("TEXT AND LAYOUT FROM NEWS.JSON - NO CLOCK, NO RANDOMNESS, NO NETWORK",
            left, y, SOFT)
    cv.text_right("PAGE 1 OF 1", right, y, SOFT)
    y += LINE_HEIGHT + 10

    if y >= cv.height:
        sys.stderr.write("content overflowed the %d px buffer at y=%d\n"
                         % (cv.height, y))
        raise SystemExit(2)

    return cv.crop(40)


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    fixture = os.path.join(here, "news.json")
    doc = load_fixture(fixture)

    if "--check" in argv:
        first = compose(doc)
        second = compose(doc)
        a = first.png_bytes()
        b = second.png_bytes()
        if a != b:
            sys.stderr.write("FAIL: two renders differ\n")
            return 1
        print("OK deterministic, %d bytes" % len(a))
        return 0

    canvas = compose(doc)

    if "--stats" in argv:
        weights = [float(s["weight"]) for s in doc["stories"]]
        print("stories        %d" % len(weights))
        print("total weight   %g" % sum(weights))
        print("rendered height %d" % canvas.height)
        return 0

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or os.path.join(here, "out")
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError:
        out_dir = "/tmp"
    # The grader picks the entry up from the output directory under a fixed
    # name; a local run keeps the dated name beside it for humans.
    target = os.path.join(out_dir, "entry.png")
    data = canvas.png_bytes()
    with open(target, "wb") as handle:
        handle.write(data)
    dated = os.path.join(here, "out", "2026-11-20.png")
    if out_dir != os.path.join(here, "out"):
        try:
            os.makedirs(os.path.dirname(dated), exist_ok=True)
            with open(dated, "wb") as handle:
                handle.write(data)
        except OSError:
            dated = target
    print("wrote %s (%d bytes, %dx%d)" % (target, len(data), canvas.width, canvas.height))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
