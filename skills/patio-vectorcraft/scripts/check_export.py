#!/usr/bin/env python3
"""Read-only SVG/DXF checks: explicit units, Patio SVG viewBox convention and supported outline closure."""
import math, re, sys
from pathlib import Path
import xml.etree.ElementTree as ET

def check_svg(p):
    root = ET.parse(p).getroot()
    w, h, vb = root.get("width", ""), root.get("height", ""), root.get("viewBox", "")
    unit = re.sub(r"[\d.\s]", "", w) or "(user units)"
    paths = [e for e in root.iter() if e.tag.split("}")[-1] in ("path", "polygon", "polyline", "rect", "circle", "ellipse")]
    open_paths = []
    for e in paths:
        tag = e.tag.split("}")[-1]
        if tag == "path" and not re.search(r"[zZ]\s*$", (e.get("d") or "").strip()):
            open_paths.append(e.get("id") or "(no id)")
        if tag == "polyline":
            open_paths.append(e.get("id") or "(polyline)")
    print(f"{p.name}: SVG width={w or '?'} height={h or '?'} unit={unit} viewBox={vb or '?'}")
    print(f"  shapes={len(paths)} open={len(open_paths)}" + (f" -> {open_paths}" if open_paths else ""))
    # Patio's delivery convention uses explicit mm on both dimensions and a mm viewBox.
    # SVG itself also permits other viewBoxes; their physical size is not inherently wrong.
    phys_ok = False
    try:
        if not (w.endswith("mm") and h.endswith("mm")):
            raise ValueError("both width and height must use mm")
        ww, hh = float(w[:-2]), float(h[:-2])
        coords = [float(x) for x in vb.replace(",", " ").split()]
        if len(coords) != 4 or not all(math.isfinite(n) for n in [ww, hh, *coords]):
            raise ValueError("a finite four-number viewBox is required")
        phys_ok = ww > 0 and hh > 0 and abs(coords[2] - ww) < 0.01 and abs(coords[3] - hh) < 0.01
        if not phys_ok:
            print("  dimensions/viewBox do not meet the Patio 1:1 mm convention")
    except ValueError as exc:
        print(f"  not a Patio mm delivery: {exc}; preserve the raw export and check the normalized copy")
    if not paths:
        print("  no supported cut outlines found")
    return bool(paths) and not open_paths and phys_ok

def check_dxf(p):
    lines = p.read_text(errors="replace").splitlines()
    pairs = list(zip(lines[0::2], lines[1::2]))
    units = None
    for i, (c, v) in enumerate(pairs):
        if c.strip() == "9" and v.strip() == "$INSUNITS" and i + 1 < len(pairs) and pairs[i + 1][0].strip() == "70":
            units = pairs[i + 1][1].strip()
            break
    polys, open_polys = 0, 0
    i = 0
    while i < len(pairs):
        c, v = pairs[i]
        if c.strip() == "0" and v.strip() in ("LWPOLYLINE", "POLYLINE"):
            polys += 1
            flag = 0
            j = i + 1
            while j < len(pairs) and pairs[j][0].strip() != "0":
                if pairs[j][0].strip() == "70":
                    flag = int(pairs[j][1].strip() or 0)
                j += 1
            if not flag & 1:
                open_polys += 1
            i = j
        else:
            i += 1
    unit_name = {"4": "mm", "1": "inches", "0": "unitless"}.get(units, units)
    print(f"{p.name}: DXF units={unit_name} polylines={polys} open={open_polys}")
    return polys > 0 and open_polys == 0 and units == "4"

def main():
    ok = True
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.suffix.lower() == ".svg":
            ok &= check_svg(p)
        elif p.suffix.lower() == ".dxf":
            ok &= check_dxf(p)
        else:
            print(f"{p.name}: skipped (not svg/dxf)")
    if len(sys.argv) < 2:
        print("usage: check_export.py <file.svg|file.dxf> ...")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
