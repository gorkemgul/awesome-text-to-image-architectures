#!/usr/bin/env python3
"""Find, download and register model figures (helper; not needed to build the catalog).

  List candidate figures in an arXiv HTML paper:
    python3 scripts/add_figure.py list 2310.00426
  Download a figure, convert it to PNG and print its figures.json record:
    python3 scripts/add_figure.py fetch pixart-alpha --origin-url URL --source-url URL --locator "Figure 2"
  Register a PNG you prepared yourself (PDF crop, assembled panels):
    python3 scripts/add_figure.py fetch ID --file crop.png --origin-url URL [--origin-url URL2 ...] ...
  Register a generated input/output diagram:
    python3 scripts/add_figure.py io ID --source-url URL

`fetch` and `io` print JSON only; with --write they update data/figures.json directly (orchestrator
use). Raster conversion uses macOS `sips`, SVG rasterization uses `qlmanage`; elsewhere supply
--file.
"""

import argparse
from hashlib import sha256
from html import unescape
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from urllib.parse import urljoin

from net import get

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "architectures"
MANIFEST = ROOT / "data" / "figures.json"


def list_figures(arxiv_id):
    final_url, raw = get(f"https://arxiv.org/html/{arxiv_id}")
    html = raw.decode("utf-8", "replace")
    # Top-level figures have ids like S4.F2 (panels are S4.F2.sf1); slice between them.
    starts = [m.start() for m in re.finditer(r'<figure id="[^"]*\bF\d+"', html)]
    for start, end in zip(starts, starts[1:] + [len(html)]):
        body, text = html[start:end], None
        for caption in re.finditer(r"<figcaption.*?</figcaption>", body, re.S):
            label = " ".join(unescape(re.sub(r"<[^>]+>", " ", caption.group(0))).split())
            if label.startswith("Figure"):
                body, text = body[:caption.end()], label
                break
        if not text:
            continue
        images = [urljoin(final_url, unescape(src)) for src in re.findall(r'<img[^>]*src="([^"]+)"', body)]
        inline = "<svg" in body
        print(text[:160])
        for image in images:
            print("   ", image)
        if not images:
            print("    (no image file" + ("; inline SVG/TikZ — crop from the PDF and use --file)" if inline else ")"))


def to_png(data, suffix):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return data
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"figure{suffix}"
        src.write_bytes(data)
        if suffix == ".svg" or data.lstrip()[:5] in (b"<?xml", b"<svg "):
            src = src.with_suffix(".svg")
            src.write_bytes(data)
            if not shutil.which("qlmanage"):
                raise SystemExit("SVG figure: rasterize it yourself and pass --file")
            subprocess.run(["qlmanage", "-t", "-s", "2000", "-o", tmp, str(src)], check=True, capture_output=True)
            return (Path(tmp) / (src.name + ".png")).read_bytes()
        if not shutil.which("sips"):
            raise SystemExit("Non-PNG figure: convert it yourself and pass --file")
        out = Path(tmp) / "out.png"
        subprocess.run(["sips", "-s", "format", "png", str(src), "--out", str(out)], check=True, capture_output=True)
        return out.read_bytes()


def emit(mid, record, write):
    if write:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest["models"][mid] = record
        manifest["models"] = dict(sorted(manifest["models"].items()))
        MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({mid: record}, indent=1, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list")
    p_list.add_argument("arxiv_id")
    p_fetch = sub.add_parser("fetch")
    p_fetch.add_argument("model_id")
    p_fetch.add_argument("--origin-url", action="append", required=True, help="Exact image URL; repeat for assembled panels")
    p_fetch.add_argument("--source-url", required=True, help="One of the model's primary source URLs")
    p_fetch.add_argument("--locator", required=True, help='e.g. "Figure 2"')
    p_fetch.add_argument("--file", type=Path, help="Use this prepared PNG instead of downloading")
    p_fetch.add_argument("--write", action="store_true")
    p_io = sub.add_parser("io")
    p_io.add_argument("model_id")
    p_io.add_argument("--source-url", required=True)
    p_io.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if args.command == "list":
        list_figures(args.arxiv_id)
        return 0
    if args.command == "io":
        emit(args.model_id, {"kind": "io-diagram", "path": f"assets/architectures/{args.model_id}.svg", "source_url": args.source_url, "origin_url": None, "locator": "Input/output diagram", "sha256": None}, args.write)
        return 0
    if args.file:
        data = args.file.read_bytes()
    else:
        if len(args.origin_url) > 1:
            raise SystemExit("Multiple panels: assemble them yourself and pass --file")
        final_url, data = get(args.origin_url[0])
        data = to_png(data, Path(final_url).suffix.lower())
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise SystemExit("Figure is not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    if width < 160 or height < 60:
        raise SystemExit(f"Figure too small ({width}x{height})")
    path = ASSETS / f"{args.model_id}.png"
    path.write_bytes(data)
    record = {"kind": "source-figure", "path": f"assets/architectures/{path.name}", "source_url": args.source_url, "origin_url": args.origin_url[0], "locator": args.locator, "sha256": sha256(data).hexdigest()}
    if len(args.origin_url) > 1:
        record["origin_urls"] = args.origin_url
    emit(args.model_id, record, args.write)
    print(f"saved {path.relative_to(ROOT)} ({width}x{height})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
