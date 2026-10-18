"""Record a demo GIF of mcp-dev-toolbox using REAL tool output.

Run from the repo root (the folder containing server.py):

    pip install pillow
    python scripts/make_demo_gif.py

It calls the same tool functions the MCP server exposes (build_index,
semantic_search, git_log) against this repo itself, then renders the
calls and their actual output as an animated terminal at docs/demo.gif.
"""
import asyncio
import os
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.environ["WORKSPACE_ROOT"] = str(REPO)  # index this repo itself
# keep the demo tooling and its output out of the index
os.environ["EXCLUDED_DIRS"] = ".git,__pycache__,.venv,venv,node_modules,.mcp_index,scripts,docs,tests"
sys.path.insert(0, str(REPO))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

# ---------------------------------------------------------------- tool capture
class _Collector:
    """Stands in for FastMCP so we can call the registered tool functions."""
    def __init__(self):
        self.tools = {}

    def tool(self, *a, **k):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn
        return deco

from mcp_dev_toolbox.tools import git_tools, semantic_search  # noqa: E402

mcp = _Collector()
git_tools.register(mcp)
semantic_search.register(mcp)
T = mcp.tools

SCENES = [
    ("build_index()", lambda: T["build_index"]()),
    ('semantic_search("where are paths checked against the workspace root?", top_k=3)',
     lambda: T["semantic_search"]("where are paths checked against the workspace root?", top_k=3)),
    ('semantic_search("how is the embedding model loaded", top_k=3)',
     lambda: T["semantic_search"]("how is the embedding model loaded", top_k=3)),
    ("git_log(max_count=4)", lambda: T["git_log"](max_count=4)),
]

# ---------------------------------------------------------------- rendering
W, H = 1000, 560
PAD_X, TOP = 22, 54
FONT_SIZE, LINE_H = 15, 21
COLS = 108
ROWS = (H - TOP - 16) // LINE_H

BG, BAR, FG, DIM = (22, 24, 30), (40, 43, 52), (221, 224, 232), (125, 132, 150)
ACCENT, PROMPT, HIT = (130, 170, 255), (126, 211, 150), (240, 190, 110)


def _font():
    for p in ("C:/Windows/Fonts/CascadiaMono.ttf",
              "C:/Windows/Fonts/consola.ttf",
              "/System/Library/Fonts/Menlo.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, FONT_SIZE)
    return ImageFont.load_default(size=FONT_SIZE)


FONT = _font()


def _wrap(text):
    out = []
    for line in text.splitlines() or [""]:
        out.extend(textwrap.wrap(line, COLS, subsequent_indent="      ",
                                 drop_whitespace=False) or [""])
    return out


def _color(line):
    s = line.lstrip()
    if s.startswith("$ "):
        return PROMPT
    if s.startswith("#"):
        return DIM
    if s.startswith("[") and "score=" in s:
        return HIT
    return FG


def _frame(lines):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 34], fill=BAR)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([16 + i * 22, 11, 28 + i * 22, 23], fill=c)
    d.text((W // 2, 17), "mcp-dev-toolbox  ·  real tool output", font=FONT,
           fill=DIM, anchor="mm")
    for i, line in enumerate(lines[-ROWS:]):
        d.text((PAD_X, TOP + i * LINE_H), line, font=FONT, fill=_color(line))
    return img


def main():
    frames, durations = [], []

    def add(lines, ms):
        frames.append(_frame(lines))
        durations.append(ms)

    screen = ["# An MCP client (Claude, Cursor...) calls these tools for you.",
              "# Semantic search runs fully locally - no API key.", ""]
    add(screen, 1400)

    for call, run in SCENES:
        prompt = "$ " + call  # ASCII prompt renders in every font
        for n in range(8, len(prompt) + 8, 8):          # typing effect
            add(screen + [prompt[:n]], 40)
        screen = screen + [prompt]
        add(screen, 400)
        print(f"running {call} ...", flush=True)
        output = asyncio.run(run())
        for line in _wrap(output.rstrip()):              # reveal output
            screen = screen + [line]
            add(screen, 90)
        screen = screen + [""]
        add(screen, 2200)

    out = REPO / "docs" / "demo.gif"
    out.parent.mkdir(exist_ok=True)
    # one shared palette lets the GIF store only what changes between frames
    ref = frames[-1].quantize(colors=32, method=Image.Quantize.MEDIANCUT)
    pal = [f.quantize(palette=ref, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durations,
                loop=0, optimize=True)
    print(f"wrote {out}  ({len(frames)} frames, {out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
