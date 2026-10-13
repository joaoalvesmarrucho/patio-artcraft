# patio-artcraft

Agent skills for the ArtCraft suite of open-source creative tools, written by Patio for design studios. One skill per Craft app, all sharing the same three rules: one job in one folder with two confined roots, files that come in by copy, and only pinned official releases installed on purpose.

The skills use only ArtCraft's official tooling: the `<app>-cli mcp` server and the `--automation-read-root` / `--automation-write-root` flags that ship with each app. They install only pinned official releases, hash-checked, on a person's command, and never during a job. The roots constrain agent-supplied file paths; they are not an operating-system sandbox. They are not affiliated with ArtCraft or storytold, and they are not a fork of any community plugin.

## Skills

| Skill | App | Status |
|---|---|---|
| `patio-vectorcraft` | VectorCraft (vector drawing, technical outlines for CNC and laser) | v0.1.0 |
| `patio-photocraft` | PhotoCraft | planned |
| `patio-effectcraft` | EffectCraft | planned |

Scope is fixed by the official documentation: on 12 October 2026 only VectorCraft, PhotoCraft and EffectCraft document the MCP server with folder confinement. FilmCraft states it has no folder limits; the other Craft apps ship a CLI but document no confinement. Other apps need documented and verified confinement before joining.

`tools/pipeline.py` runs a plan across apps in one project: dependency order, a ledger with content hashes, resume, per-node and per-plan time budgets, supervision that kills a stuck run, and a confined MCP reopen check of every output. See `docs/pipeline.md` and `examples/`.

## Install

Requires macOS, Python 3.10+, and an MCP-capable assistant such as Claude Code or Codex. Clone a tagged release; the skill uses the repository's `tools/` and `pins/` folders, so keep the whole checkout.

```bash
git clone --branch v0.1.0 https://github.com/joaoalvesmarrucho/patio-artcraft.git
cd patio-artcraft
```

Three commands and you are drawing:

```bash
python3 tools/patio_artcraft.py setup                                # once: official VectorCraft release, hash-checked
python3 tools/patio_artcraft.py new-project ~/Jobs/S01 --client "Studio X"
python3 tools/patio_artcraft.py serve ~/Jobs/S01 --write-config       # writes the MCP config; your assistant starts the server
```

The assistant then follows `skills/patio-vectorcraft/SKILL.md`. Files from outside the job come in with `bring`, as copies. Repetitive drawing is sent as one batch, so a 240-shape pattern draws in milliseconds.

## Why these rules

Patio reviewed the unofficial PartMe.AI artcraft-use wrapper in October 2026. The source review found a conditional low-severity file-write issue in its project runner and separate exposure to changing optional dependencies; it found no obvious malicious instructions. This project uses the official app route, pinned releases and explicit job-file roots. Read the review at patio.consulting/artcraft-review.

## Licence

MIT. See `LICENSE`.
