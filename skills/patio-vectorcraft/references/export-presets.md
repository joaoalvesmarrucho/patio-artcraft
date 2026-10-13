# Export presets — VectorCraft 0.9.0

Verified with the pinned official macOS CLI on 12 October 2026. Coordinates for `shape.rectangle` and other numeric drawing commands are points: multiply millimetres by 72/25.4. `file.new` accepts strings such as `"1450 mm"`, with `units: "Millimeters"`.

## SVG: preserve the raw file and normalize a copy

No documented SVG option in `document.formats` sets physical millimetre width/height. This tested MCP export:

```json
{"path":"<project>/out/S01_raw.svg","format":"svg","options":{"decimals":3,"responsive":false,"useArtboards":true}}
```

produces unitless `width="4110.236" height="481.89"` and `viewBox="0 0 4110.236 481.89"` for a 1450 × 170 mm artboard. Setting document units to Millimeters does not change that export behavior. `responsive: true` omits width/height; it does not make a millimetre cutting file.

Keep the raw SVG. In a separate `_1to1mm.svg` copy, the pipeline sets width=1450mm, height=170mm and viewBox="0 0 1450 170", then wraps the unchanged content in the corresponding scale/translate transform. It checks the aspect ratio before writing. The raw file, normalized file and both hashes remain in the ledger. This is Patio normalization, not an undocumented native export feature.

The checker enforces this Patio mm-viewBox convention, closed supported outlines and explicit mm dimensions. SVG permits other valid viewBox scales; a different viewBox is not by itself an invalid physical size. These checks are not a complete manufacturing geometry audit.

## Native, DXF and review files

| Deliverable | Verified route | Notes |
|---|---|---|
| Editable master | MCP `save_file` to `.vectorcraft` before exports | Reopen with `open_file`, then inspect the document. |
| Raw SVG | MCP `export`, options above | Archive; not labelled as a mm delivery. |
| Cut SVG | Separate normalized `_1to1mm.svg` | Run `check_export.py`; retain raw source. |
| DXF | MCP `export`, format `dxf`, options `{"unit":"Millimeters","scale":1,"version":"2013","useArtboards":true}` | Native export; no SVG conversion needed. Tested S01 has `$INSUNITS=4` and one closed 12-vertex polyline, 1450 × 170 mm. |
| Review sheet | MCP `export`, format `pdf` | Add dimensions and REVIEW status to a separate review artboard. |
| Preview | PNG; PhotoCraft example uses 2000 × 800 px | Presentation only, never a cutting file. |

SVG and DXF are geometry exchange files, not machine programs. The workshop reviews dimensions, material, toolpaths and machine settings before production.
