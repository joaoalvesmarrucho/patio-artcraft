---
name: patio-vectorcraft
description: Produce and revise editable VectorCraft drawings (technical outlines, panels, cut files for CNC and laser) through ArtCraft's official MCP server, confined to one project folder, using Patio's production conventions. Use when a studio asks for vector drawings or cutting files and VectorCraft is installed.
license: MIT
---

# Patio VectorCraft skill

You draw in VectorCraft through its official MCP server. You never install software during a drawing job, widen the configured file roots, or resume a project you have not been shown. The roots limit agent-supplied paths; they are not an operating-system sandbox.

## Before you start

One-time, by a person: `python3 tools/patio_artcraft.py setup` (downloads the pinned official VectorCraft CLI, checks its hash, records the version).

Per job, one command: `python3 tools/patio_artcraft.py new-project <folder> --client <name>` then `serve <folder> --write-config`. That creates the layout, the project record and the confined MCP configuration. The MCP client starts the server from the written configuration. Watched desktop sessions require a separately installed app and verified configuration; the CLI-only setup does not install that app.

Run the following commands from the complete repository checkout.

Then:
1. Run `python3 skills/patio-vectorcraft/scripts/check_setup.py --project <project>` (read-only). If it reports NOT READY, tell the person which command fixes it; do not improvise an install.
2. Confirm the MCP server has both roots. A refused-path error during work means you asked for something outside the roots: fix the path, never the roots.
3. Need a file that is outside the project? `python3 tools/patio_artcraft.py bring <project> <file>` copies it into `sources/`. Ask the person once, then bring it.
4. Read `<project>/brief/` and restate: units (millimetres for cut files), material thickness, revision letter, deliverables. Ask about anything missing before drawing.

## Layout, naming and exports

Follow `references/project-layout.md`, `references/export-presets.md` and `references/review-checklist.md`. Short version: everything you write goes to `<project>/out/`; files are named `S01_<part>_<W>x<H>mm_rev<letter>`; one artboard per part, named the same way; cut files are 1:1 mm SVG, DXF only when the workshop asks; every delivery carries a REVIEW mark until a person approves it.

## Drawing

- Send drawing as `command_batch` calls, one batch per part or per logical step (for example all shapes of a pattern), not one `run_command` per object. The official runtime has a fixed cost per request: 480 single calls take about 0.3 s, the same steps as one batch about 7 ms. Use `"$N.path"` / `"$last.path"` to reuse an earlier step's result (an id) inside the batch, keep `stop_on_error` on, and use single `run_command` calls only for queries or when the next step depends on reading the result.
- Use `references/commands-0.9.0.json` is the command reference for the pinned release; use it instead of guessing. If a command is missing there, query `vectorcraft-cli commands` once and note it in the hand-off.
- Create the document with explicit units and size, then one artboard per part. Draw outlines as closed paths. Notches and holes are part of the same closed outline or separate closed paths, never open strokes.
- Save the native `.vectorcraft` file to `out/` before any export. Export raw SVG, then use the documented normalization to create a separate 1:1 mm delivery copy. The v0.9.0 SVG exporter has no documented mm-size option. Export a PDF review sheet with dimensions annotated.
- Run `python3 skills/patio-vectorcraft/scripts/check_export.py <file>` on the normalized SVG and DXF delivery copies. Preserve the raw SVG as export evidence; its unitless dimensions are expected to fail this delivery check. Report the delivery checks verbatim in the hand-off note.

## Hand-off

Write `out/README.md` with: what was drawn, each part's dimensions, revision letter, the checks run and their results, and the caveat that SVG and DXF are geometry exchange files, not machine programs; the workshop produces its own toolpaths. Deliver directly. If the project record has `releaseGate: person`, mark the files REVIEW and ask for sign-off before they are sent.

## Never

- Never install or update software during a job. Installing is `setup`, run by a person, from the pin.
- Never widen the roots or point them at a shared drive.
- Never link or place a file from outside the read root; `bring` it in as a copy.
- Never open a project folder that arrived from outside the studio before a person has looked inside it.
- Never send cut files to a workshop while the project record's release gate is `person` and nobody has signed.
