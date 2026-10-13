# Confined MCP pipeline

`python3 tools/pipeline.py <project> examples/shelf-and-poster.plan.json` runs the tested two-app example through the official pinned MCP servers. It never uses `run`: VectorCraft 0.9.0 rejects both automation-root flags on that subcommand. `info <file>` exists, but reopen checks use the same confined MCP session instead of an unrestricted `info` call.

Each node starts `<app>-cli mcp --automation-read-root <project> --automation-write-root <project>/out`. VectorCraft and PhotoCraft adapters are verified. EffectCraft is pinned and installed for hash/version verification only; its pipeline adapter and dedicated skill remain unimplemented. This is application-level control of agent-supplied paths, not an OS sandbox. Application-managed preferences, recovery, fonts and libraries are outside the claimed job-file boundary.

Plans declare inputs, steps, exports and every output. The runner orders dependencies, rejects escaping or symlinked paths, and checks each CLI binary against its pin. It saves native files and exports, reopens every output through MCP, and applies the SVG/DXF checks named in `geometryFiles`. `normalizeSvg` makes a separate mm copy while preserving the raw SVG; see the VectorCraft export presets.

`out/ledger.json` records tool calls/results, input/output hashes, CLI hash, timings and checks. On resume, a node is skipped only when its plan/revision, binary hash, inputs and all outputs still match. A changed node rebuilds before its dependents. The node and total budgets also cover reopen checks. Each MCP process runs in its own process group and is terminated at its deadline; a stale `out/running.json` marks an interrupted prior run. This does not protect against a malicious local process racing filesystem checks.

The sample uses real catalogue commands: `shape.rectangle`, `select.all`, `object.pathfinder.minusFront`, then PhotoCraft `image.imageSize` and `image.canvasSize`. It subtracts two 30 × 30 mm notches from a 1450 × 170 mm shelf and creates a raster presentation preview. The PNG is not a cutting file.

Verification: `examples/runtime-verification-20261012.json` and the sanitized `examples/shelf-and-poster.ledger.sample.json`. The ledger's times cover local commands and checks only; they exclude installation, planning and human review.
