#!/usr/bin/env python3
"""Read-only setup check for the patio-vectorcraft skill. Installs nothing, writes nothing."""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

PIN = Path(__file__).resolve().parents[3] / "pins" / "vectorcraft.lock.json"

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", required=True, help="project folder (becomes the read root)")
    ap.add_argument("--cli", default=None, help="path to vectorcraft-cli (default: the setup-installed one)")
    a = ap.parse_args()
    problems = []
    pin = json.loads(PIN.read_text())
    if a.cli is None:
        home = Path(__import__('os').environ.get('PATIO_ARTCRAFT_HOME', Path.home()/'.patio-artcraft'))
        cand = home/'vectorcraft'/pin['version']/'vectorcraft-cli'
        a.cli = str(cand) if cand.is_file() else shutil.which('vectorcraft-cli')
    if not a.cli or not Path(a.cli).is_file():
        problems.append("vectorcraft-cli not installed; a person runs: python3 tools/patio_artcraft.py setup")
    else:
        cli = Path(a.cli).resolve()
        if "TO_BE_RECORDED" in pin.get("cliSha256", ""):
            problems.append("pins/vectorcraft-cli.lock.json has no recorded cliSha256; the studio must record it from the official release")
        elif sha256(cli) != pin["cliSha256"]:
            problems.append("vectorcraft-cli hash does not match the pinned hash; do not proceed, ask the studio owner")
        else:
            try:
                v = subprocess.run([str(cli), "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
            except Exception as e:
                v = f"error: {e}"
            if pin["version"] not in v:
                problems.append(f"vectorcraft-cli reports '{v}', pin expects {pin['version']}")
    raw_project = Path(a.project).expanduser()
    if raw_project.is_symlink():
        problems.append("project folder is a symbolic link; use a plain folder")
    project = raw_project.resolve()
    out = project / "out"
    for d in (project, project / "brief", out):
        if not d.is_dir():
            problems.append(f"missing folder: {d}")
    if out.is_symlink():
        problems.append("project or out folder is a symbolic link; use a plain folder")
    print("patio-vectorcraft setup check")
    print(f"  pin: VectorCraft {pin['version']} ({pin['asset']})")
    print(f"  read root : {project}")
    print(f"  write root: {out}")
    if problems:
        print("NOT READY:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("READY. Start the server with:")
    print(f'  "{a.cli}" mcp --automation-read-root "{project}" --automation-write-root "{out}"')

if __name__ == "__main__":
    main()
