# Changelog

## v0.1.0 — 13 October 2026

- Drawing is sent as one `command_batch` per pipeline node, and the skill tells agents to batch repetitive drawing. The official runtime charges a fixed cost per MCP request (about 0.3 ms); a 240-shape pattern's drawing drops from about 170 ms to about 7 ms. Single commands remain the fallback when an app has no batch tool.
- `tools/pipeline.py` resolves its own imports under `python3 -I`.

- Skeleton: repo layout, `patio-vectorcraft` draft skill, read-only check scripts, project record template.
- tools: setup / new-project / bring / serve; pipeline with ledger, resume, budgets, supervision, reopen checks (tested against a stub CLI).
- Release gate defaults to none.
- 2026-10-12: pinned official CLI setup verified for VectorCraft 0.9.0, PhotoCraft 0.7.0 and EffectCraft 0.8.0; archive and extracted binary SHA-256 recorded.
- Replaced unconfined `run` pipeline with app-specific official MCP adapters for VectorCraft and PhotoCraft; both tested with read/write-root refusal probes. EffectCraft adapter remains pending.
- Corrected sample command names, point/mm units, boolean notch subtraction, native DXF export, separate normalized SVG, and visible PhotoCraft preview. Reopened all six outputs; verified resume and selective rebuild.
- Added actual catalogue, export presets, sanitized ledger and runtime evidence. Path checks inspect symlinks before resolution; CLI-only setup no longer promises an unverified watched desktop launch.
- Before first tag: verify standalone skill packaging (currently use a complete checkout) and run independent forward testing. No repository/tag has been published by this verification.
