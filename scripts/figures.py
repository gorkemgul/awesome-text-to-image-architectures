"""Figure provenance, local asset checks and reproducible interface diagrams.

Adapted from kadirnar/awesome-tts-architectures (Apache-2.0); modified for text-to-image models.
"""

from collections import Counter
from hashlib import sha256
from html import escape
from pathlib import Path
import re
import struct
import textwrap
from urllib.parse import urlsplit

MODALITY_NAMES = {"T": "Text", "I": "Images", "V": "Video", "A": "Audio"}


def validate_figures(catalog, manifest, root):
    models = {m["id"]: m for m in catalog["models"]}
    if manifest.get("schema_version") != 1 or set(manifest.get("models", {})) != set(models):
        raise ValueError("Figure manifest must contain exactly one record per model")
    required = {"kind", "path", "source_url", "origin_url", "locator", "sha256"}
    checked = set()
    for mid, figure in manifest["models"].items():
        if not required <= set(figure) or set(figure) - required - {"origin_urls", "diagram"} or figure["kind"] not in {"source-figure", "io-diagram", "architecture-diagram"}:
            raise ValueError(f"{mid}: invalid figure fields/kind")
        if "origin_urls" in figure:
            origins = figure["origin_urls"]
            if figure["kind"] != "source-figure" or not isinstance(origins, list) or len(origins) < 2 or len(set(origins)) != len(origins) or origins[0] != figure["origin_url"]:
                raise ValueError(f"{mid}: invalid multi-panel figure origins")
            for origin_url in origins:
                origin = urlsplit(origin_url)
                if origin.scheme != "https" or not origin.netloc or origin.username or origin.password or re.search(r"\s", origin_url):
                    raise ValueError(f"{mid}: invalid panel origin URL")
        if figure["source_url"] not in {s["url"] for s in models[mid]["sources"]}:
            raise ValueError(f"{mid}: figure must cite one of the model's primary sources")
        path = Path(figure["path"])
        expected_suffix = ".svg" if figure["kind"] != "source-figure" else ".png"
        if path.parent.as_posix() != "assets/architectures" or path.suffix != expected_suffix:
            raise ValueError(f"{mid}: invalid local figure path")
        if not figure["locator"].strip():
            raise ValueError(f"{mid}: missing figure locator")
        if figure["kind"] != "architecture-diagram" and "diagram" in figure:
            raise ValueError(f"{mid}: diagram data requires an architecture diagram")
        if figure["kind"] in {"io-diagram", "architecture-diagram"}:
            if figure["kind"] == "architecture-diagram":
                validate_architecture(figure.get("diagram", {}))
            if path.name != f"{mid}.svg" or figure["origin_url"] is not None or figure["sha256"] is not None:
                raise ValueError(f"{mid}: interface diagrams must be generated locally")
            continue
        origin = urlsplit(figure["origin_url"])
        if origin.scheme != "https" or not origin.netloc or origin.username or origin.password or re.search(r"\s", figure["origin_url"]):
            raise ValueError(f"{mid}: invalid figure origin URL")
        if not re.fullmatch(r"[0-9a-f]{64}", figure["sha256"]):
            raise ValueError(f"{mid}: invalid asset checksum")
        signature = (figure["path"], figure["sha256"])
        if signature in checked:
            continue
        data = (root / path).read_bytes()
        if sha256(data).hexdigest() != figure["sha256"]:
            raise ValueError(f"{mid}: figure checksum mismatch")
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            raise ValueError(f"{mid}: figure is not a PNG")
        width, height = struct.unpack(">II", data[16:24])
        if width < 160 or height < 60:
            raise ValueError(f"{mid}: figure is too small to read")
        checked.add(signature)


def render_interface(model):
    """Show only documented input/output sets; do not infer internal connections."""
    name = escape(model["name"])
    title_lines = textwrap.wrap(model["name"], width=49)
    architecture = textwrap.wrap(model["architecture"], width=36)
    rows = max(len(model["inputs"]), len(model["outputs"]), 3)
    top = 112 + (len(title_lines) - 1) * 38
    body_height = max(rows * 46 + 50, 250)
    height = top + body_height + 82
    center = top + body_height / 2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="{height}" viewBox="0 0 1120 {height}" role="img" aria-labelledby="title desc">',
        f"<title id=\"title\">{name}: documented inputs and outputs</title>",
        "<desc id=\"desc\">Editorial interface diagram. Internal architecture and per-task modality combinations are not shown. See the model notes and primary sources.</desc>",
        '<rect width="1120" height="100%" rx="18" fill="#f8fafc"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        '<text x="42" y="33" font-size="13" font-weight="700" letter-spacing="2" fill="#64748b">DOCUMENTED INTERFACE · EDITORIAL DIAGRAM</text>',
    ]
    for index, title in enumerate(title_lines):
        parts.append(f'<text x="42" y="{76 + index * 38}" font-size="32" font-weight="700" fill="#0f172a">{escape(title)}</text>')
    parts += [
        f'<rect x="365" y="{center - 97}" width="390" height="194" rx="16" fill="#ffffff" stroke="#cbd5e1" stroke-width="2"/>',
        f'<text x="560" y="{center - 60}" text-anchor="middle" font-size="12" font-weight="700" letter-spacing="2" fill="#64748b">MODEL / SYSTEM</text>',
    ]
    start = center - (len(architecture) - 1) * 13
    for index, line in enumerate(architecture):
        parts.append(f'<text x="560" y="{start + index * 26}" text-anchor="middle" font-size="19" font-weight="600" fill="#0f172a">{escape(line)}</text>')
    parts.append(f'<text x="560" y="{center + 67}" text-anchor="middle" font-size="14" fill="#64748b">{escape(model["interaction"])}</text>')
    for side, x, color in [("inputs", 42, "#0369a1"), ("outputs", 842, "#047857")]:
        values = model[side]
        parts.append(f'<text x="{x}" y="{top + 10}" font-size="13" font-weight="700" letter-spacing="2" fill="{color}">{side.upper()}</text>')
        first = center - (len(values) * 46 - 10) / 2
        for index, modality in enumerate(values):
            y = first + index * 46
            parts += [
                f'<rect x="{x}" y="{y}" width="236" height="36" rx="8" fill="#ffffff" stroke="#cbd5e1"/>',
                f'<text x="{x + 14}" y="{y + 24}" font-size="17" fill="{color}">{MODALITY_NAMES[modality]}</text>',
            ]
    parts += [
        f'<path d="M292 {center} H346 M337 {center - 7} L347 {center} L337 {center + 7}" fill="none" stroke="#0369a1" stroke-width="2.5"/>',
        f'<path d="M773 {center} H827 M818 {center - 7} L828 {center} L818 {center + 7}" fill="none" stroke="#047857" stroke-width="2.5"/>',
        f'<text x="42" y="{height - 37}" font-size="15" fill="#64748b">Input/output summary; internal architecture is not shown. Task and variant limits apply.</text>',
        "</g></svg>",
    ]
    return "\n".join(parts) + "\n"


def render_credits(models, manifest):
    figures = manifest["models"]
    counts = Counter(f["kind"] for f in figures.values())
    lines = [
        "# Figure credits", "",
        "<!-- Generated by scripts/catalog.py from data/models.json and data/figures.json. -->", "",
        f'{counts["source-figure"]} entries show a primary-source figure; {counts["architecture-diagram"]} use a source-based architecture diagram; {counts["io-diagram"]} use an editorial input/output diagram.', "",
        "Source figures belong to their authors or publishers; see the [figure notice](FIGURE_NOTICE.md). Shared family figures can appear in more than one model entry. Interface diagrams summarize catalog metadata and do not reconstruct undisclosed internals.", "",
        "| Model | Visual | Primary source | Image origin |", "| --- | --- | --- | --- |",
    ]
    for model in models:
        figure = figures[model["id"]]
        origin = f'[Original]({figure["origin_url"]})' if figure["origin_url"] else ("Reconstructed from primary source" if figure["kind"] == "architecture-diagram" else "Generated from catalog")
        if figure.get("origin_urls"):
            origin = " · ".join(f'[Panel {n}]({url})' for n, url in enumerate(figure["origin_urls"], 1))
        lines.append(f'| {model["name"]} | [{figure["locator"]}]({Path(figure["path"]).name}) | [Source]({figure["source_url"]}) | {origin} |')
    return "\n".join(lines) + "\n"


DIAGRAM_COLORS = {
    'input': ('#e0f2fe', '#0284c7'), 'encoder': ('#ede9fe', '#7c3aed'),
    'model': ('#dbeafe', '#2563eb'), 'latent': ('#fef3c7', '#d97706'),
    'decoder': ('#ccfbf1', '#0d9488'), 'output': ('#dcfce7', '#16a34a'),
}


def validate_architecture(diagram):
    """Check authored geometry and references before rendering a reconstruction."""
    if not diagram.get('evidence', '').strip():
        raise ValueError('Architecture diagram requires a primary-source section or code reference')
    width, height = diagram['width'], diagram['height']
    if not 400 <= width <= 2400 or not 250 <= height <= 1600:
        raise ValueError('Invalid architecture diagram dimensions')
    nodes = diagram['nodes']
    ids = {n['id'] for n in nodes}
    if not nodes or len(ids) != len(nodes):
        raise ValueError('Architecture nodes must have unique IDs')
    for group in diagram.get('groups', []):
        if not group['label'].strip() or group['x'] < 0 or group['y'] < 85 or group['w'] <= 0 or group['h'] <= 0 or group['x']+group['w'] > width or group['y']+group['h'] > height:
            raise ValueError('Invalid architecture group bounds/label')
    for node in nodes:
        if node.get('visual', 'plain') not in {'plain', 'tokens', 'tensor', 'encoder', 'decoder', 'image', 'stack', 'unet'}:
            raise ValueError('Invalid architecture node visual')
        if not 10 <= node.get('font_size', 14) <= 24:
            raise ValueError('Invalid architecture font size')
        if 'layers' in node and (node.get('visual') != 'stack' or not node['layers'] or any(not isinstance(layer, str) or not layer.strip() for layer in node['layers'])):
            raise ValueError('Invalid architecture block layers')
        if node['kind'] not in DIAGRAM_COLORS or not node['label'].strip():
            raise ValueError('Invalid architecture node label/kind')
        if min(node['w'], node['h']) <= 0 or node['x'] < 0 or node['y'] < 95 or node['x'] + node['w'] > width or node['y'] + node['h'] > height - 20:
            raise ValueError(f"Architecture node out of bounds: {node['id']}")
    for edge in diagram['edges']:
        if edge['from'] not in ids or edge['to'] not in ids:
            raise ValueError('Architecture edge references an unknown node')
        if 'label_position' in edge and (len(edge['label_position']) != 2 or not 0 <= edge['label_position'][0] <= width or not 0 <= edge['label_position'][1] <= height):
            raise ValueError('Architecture edge label out of bounds')
        for x, y in edge.get('points', []):
            if not 0 <= x <= width or not 0 <= y <= height:
                raise ValueError('Architecture edge point out of bounds')


def render_architecture(model, diagram):
    """Render explicit, source-reviewed module connections, not inferred I/O sets."""
    validate_architecture(diagram)
    width, height = diagram['width'], diagram['height']
    nodes = {n['id']: n for n in diagram['nodes']}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(model["name"])} architecture</title>',
        f'<desc id="desc">Source-based reconstruction. {escape(diagram["evidence"])}</desc>',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 Z" fill="#475569"/></marker></defs>',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        '<text x="32" y="67" font-size="12" fill="#64748b">Architecture reconstructed from the cited primary source</text>',
        f'<text x="32" y="39" font-size="25" font-weight="700" fill="#0f172a">{escape(model["name"])}</text>',
    ]
    for group in diagram.get('groups', []):
        x, y, w, h = (group[k] for k in ('x', 'y', 'w', 'h'))
        color = escape(group.get('color', '#fafafa'))
        dash = ' stroke-dasharray="7 5"' if group.get('dashed', True) else ''
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{color}" stroke="#94a3b8" stroke-width="1.4"{dash}/>')
        parts.append(f'<text x="{x+14}" y="{y+23}" font-size="15" font-weight="600" fill="#334155">{escape(group["label"])}</text>')
    for edge in diagram['edges']:
        a, b = nodes[edge['from']], nodes[edge['to']]
        ax, ay = a['x'] + a['w']/2, a['y'] + a['h']/2
        bx, by = b['x'] + b['w']/2, b['y'] + b['h']/2
        points = edge.get('points')
        if not points:
            if max(a['x'], b['x']) < min(a['x']+a['w'], b['x']+b['w']):
                direction = 1 if by > ay else -1
                points = [(ax,ay+direction*a['h']/2),(bx,by-direction*b['h']/2)]
            else:
                direction = 1 if bx > ax else -1
                sx, ex = ax+direction*a['w']/2, bx-direction*b['w']/2
                points = [(sx,ay),((sx+ex)/2,ay),((sx+ex)/2,by),(ex,by)]
        route = ' '.join(f'{x},{y}' for x,y in points)
        dashed = ' stroke-dasharray="6 5"' if edge.get('dashed') else ''
        parts.append(f'<polyline points="{route}" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"{dashed}/>')
        if edge.get('label'):
            segments = list(zip(points, points[1:]))
            start, end = max(segments, key=lambda segment: abs(segment[0][0]-segment[1][0]) + abs(segment[0][1]-segment[1][1]))
            x, y = (start[0]+end[0])/2, (start[1]+end[1])/2 - 10
            x, y = edge.get('label_position', (x, y))
            label = escape(edge['label'])
            parts.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-size="13" fill="#475569" stroke="#ffffff" stroke-width="5" paint-order="stroke">{label}</text>')
    for node in nodes.values():
        parts.extend(render_paper_node(node))
    parts.append('</g></svg>')
    return '\n'.join(parts) + '\n'


def render_paper_node(node):
    """Use scientific figure conventions for modules, tensors and token streams."""
    fill, stroke = DIAGRAM_COLORS[node['kind']]
    x, y, w, h = (node[k] for k in ('x', 'y', 'w', 'h'))
    cx = x+w/2
    visual = node.get('visual', 'plain')
    font = node.get('font_size', 14)
    lines = node['label'].splitlines()
    out = []
    label_top = y+h/2 - (len(lines)-1)*(font+4)/2
    if visual == 'plain':
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
    elif visual == 'stack':
        layers = node.get('layers', [])
        for offset in (8, 4, 0):
            out.append(f'<rect x="{x+offset}" y="{y+offset}" width="{w-8}" height="{h-8}" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
        if layers:
            label_top = y+20
            top = y+len(lines)*(font+4)+28
            row_h = min(50, (h-(top-y)-20)/len(layers))
            for index, layer in enumerate(layers):
                yy = top+index*row_h
                out.append(f'<rect x="{x+18}" y="{yy}" width="{w-44}" height="{row_h-5}" rx="3" fill="#ffffff" stroke="{stroke}" stroke-width="0.9"/>')
                out.append(f'<text x="{cx-4}" y="{yy+(row_h-5)/2+4}" text-anchor="middle" font-size="12" fill="#1f2937">{escape(layer)}</text>')
    elif visual in {'encoder', 'decoder'}:
        gh = max(36, h - len(lines)*(font+4)-24)
        if visual == 'encoder':
            points = [(x+8,y+6),(x+w-8,y+6),(x+w*.72,y+gh),(x+w*.28,y+gh)]
        else:
            points = [(x+w*.28,y+6),(x+w*.72,y+6),(x+w-8,y+gh),(x+8,y+gh)]
        out.append(f'<polygon points="{" ".join(f"{a},{b}" for a,b in points)}" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
        label_top = y+gh+18
    elif visual == 'tokens':
        count, gap = 6, 6
        bw = min(30,(w-20-gap*(count-1))/count)
        left = cx-(count*bw+(count-1)*gap)/2
        for i in range(count):
            xx = left+i*(bw+gap)
            out.append(f'<rect x="{xx}" y="{y+10}" width="{bw}" height="30" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')
            if i in (2,3):
                out.append(f'<text x="{xx+bw/2}" y="{y+30}" font-family="Georgia,serif" font-size="15" text-anchor="middle" fill="{stroke}">⋯</text>')
        label_top = y+60
    elif visual == 'tensor':
        cw, ch = min(86,w-30), max(25,min(55,h-len(lines)*(font+4)-28))
        xx, yy = cx-cw/2-5, y+9
        for shift in (10,5,0):
            out.append(f'<rect x="{xx+shift}" y="{yy+shift}" width="{cw}" height="{ch}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>')
        for i in range(1,5):
            out.append(f'<path d="M{xx+i*cw/5} {yy} v{ch} M{xx} {yy+i*ch/5} h{cw}" stroke="{stroke}" stroke-width="0.55" opacity="0.55"/>')
        label_top = yy+ch+29
    elif visual == 'image':
        iw, ih = min(w-24,110), max(35,min(70,h-len(lines)*(font+4)-25))
        xx, yy = cx-iw/2, y+8
        out.append(f'<rect x="{xx}" y="{yy}" width="{iw}" height="{ih}" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')
        out.append(f'<circle cx="{xx+iw*.74}" cy="{yy+ih*.26}" r="{ih*.10}" fill="{stroke}" opacity="0.55"/>')
        out.append(f'<path d="M{xx+8} {yy+ih-7} L{xx+iw*.36} {yy+ih*.35} L{xx+iw*.58} {yy+ih*.72} L{xx+iw*.72} {yy+ih*.5} L{xx+iw-7} {yy+ih-7} Z" fill="{stroke}" opacity="0.35"/>')
        label_top = yy+ih+20
    elif visual == 'unet':
        gh = h-len(lines)*(font+4)-22
        left, right = x+12, x+w-45
        for i in range(3):
            yy = y+8+i*gh/3
            bh = max(13,gh/3-10)
            lx, rx = left+i*14, right-i*14
            for xx in (lx,rx):
                out.append(f'<rect x="{xx}" y="{yy}" width="33" height="{bh}" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
            out.append(f'<path d="M{lx+33} {yy+bh/2} H{rx}" fill="none" stroke="{stroke}" stroke-width="1.1" stroke-dasharray="4 3"/>')
            if i<2:
                ny = y+8+(i+1)*gh/3
                out.append(f'<path d="M{lx+16} {yy+bh} L{lx+30} {ny} M{rx+2} {ny} L{rx+16} {yy+bh}" fill="none" stroke="{stroke}" stroke-width="1.2"/>')
        bottom_y = y+8+2*gh/3+max(13,gh/3-10)/2
        out.append(f'<path d="M{left+28+33} {bottom_y} H{right-28}" fill="none" stroke="{stroke}" stroke-width="2"/>')
        label_top = y+gh+16
    for i,line in enumerate(lines):
        out.append(f'<text x="{cx}" y="{label_top+i*(font+4)+5}" text-anchor="middle" font-size="{font}" font-weight="500" fill="#111827">{escape(line)}</text>')
    return out
