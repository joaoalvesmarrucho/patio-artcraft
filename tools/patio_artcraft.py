#!/usr/bin/env python3
"""patio-artcraft: one command each for setup, new project, bringing files in, and starting a confined session.

setup        download the pinned official release, verify its hash, unzip, record the version
new-project  create a project folder with the Patio layout and write its record
bring        copy a file into <project>/sources (never a link) and log it
serve        print, write or run the confined MCP command for a project
"""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys, tempfile, urllib.request, urllib.error, ssl, zipfile
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import inside

TOOL_HOME = Path(os.environ.get("PATIO_ARTCRAFT_HOME", Path.home() / ".patio-artcraft"))
PINS = Path(__file__).resolve().parent.parent / "pins"

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def pin(app):
    return json.loads((PINS / f"{app}.lock.json").read_text())

def cli_path(app):
    p = pin(app)
    return TOOL_HOME / app / p["version"] / p["cliName"]

def cmd_setup(a):
    p = pin(a.app)
    if "TO_BE" in p["assetSha256"]:
        sys.exit(f"pins/{a.app}.lock.json has no assetSha256; Patio records it from the official release before tagging")
    target = TOOL_HOME / a.app / p["version"]
    cli = target / p["cliName"]
    if cli.is_file() and sha256(cli) == p["cliSha256"] and (target / "installed.json").is_file():
        print(f"{a.app} {p['version']} already installed at {cli}")
        return
    print(f"Downloading {p['assetUrl']}")
    with tempfile.TemporaryDirectory() as td:
        z = Path(td) / p["asset"]
        try:
            urllib.request.urlretrieve(p["assetUrl"], z)
        except urllib.error.URLError as exc:
            # macOS Python.org installs can lack a CA bundle; curl uses system trust.
            # Keep certificate verification on and still verify the pinned archive hash.
            if not isinstance(exc.reason, ssl.SSLCertVerificationError) or not shutil.which("curl"):
                raise
            subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                            "--proto", "=https", "--proto-redir", "=https", "--max-time", "180",
                            "--output", str(z), p["assetUrl"]], check=True)
        got = sha256(z)
        if got != p["assetSha256"]:
            sys.exit(f"hash mismatch: expected {p['assetSha256']}, got {got}. Nothing installed.")
        stage = Path(td) / "stage"
        with zipfile.ZipFile(z) as zf:
            for m in zf.infolist():
                if m.filename.startswith("/") or ".." in m.filename.split("/"):
                    sys.exit("archive contains an unsafe path; nothing installed")
            zf.extractall(stage)
        found = next(stage.rglob(p["cliName"]), None)
        if not found:
            sys.exit(f"{p['cliName']} not found in archive; nothing installed")
        if sha256(found) != p["cliSha256"]:
            sys.exit("CLI hash does not match the pin; nothing installed")
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(found, cli)
        cli.chmod(0o755)
    v = subprocess.run([str(cli), "--version"], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    if len(v.split()) < 2 or v.split()[1] != p["version"]:
        sys.exit(f"CLI reports {v!r}; expected {p['version']}. Setup record not written.")
    (target / "installed.json").write_text(json.dumps({"app": a.app, "version": p["version"], "assetUrl": p["assetUrl"],
        "assetSha256": p["assetSha256"], "cliSha256": p["cliSha256"], "reported": v,
        "installedOn": datetime.date.today().isoformat(), "installedBy": os.environ.get("USER", "")}, indent=2))
    print(f"Installed {a.app} {p['version']} -> {cli}\nReported version: {v}")

def project_root(value):
    raw = Path(value).expanduser()
    if raw.is_symlink():
        sys.exit("project folder must not be a symbolic link")
    return raw.resolve()

def cmd_new_project(a):
    root = project_root(a.path)
    if root.exists() and any(root.iterdir()):
        sys.exit(f"{root} exists and is not empty. A new job gets a new folder.")
    for d in ("brief", "sources", "out"):
        (root / d).mkdir(parents=True, exist_ok=True)
    rec = {"project": root.name, "client": a.client or "", "createdOn": datetime.date.today().isoformat(),
           "createdBy": os.environ.get("USER", ""), "apps": {}, "readRoot": str(root), "writeRoot": str(root / "out"),
           "approvedBy": "", "releaseGate": a.release_gate, "sourcesLog": []}
    for app in a.apps:
        inst = TOOL_HOME / app / pin(app)["version"] / "installed.json"
        rec["apps"][app] = json.loads(inst.read_text()) if inst.is_file() else "NOT INSTALLED: run setup"
    (root / "project-record.json").write_text(json.dumps(rec, indent=2))
    (root / "brief" / "README.md").write_text("# Brief\n\nPut the request here: dimensions, material, thickness, quantities, deadline, photos.\n")
    print(f"Project ready: {root}\n  read root : {root}\n  write root: {root/'out'}")
    for app in a.apps:
        print(f"  {app}: {rec['apps'][app] if isinstance(rec['apps'][app], str) else rec['apps'][app]['version']}")
    print(f"Next: patio_artcraft.py serve {root} --app {a.apps[0]} --write-config")

def cmd_bring(a):
    root = project_root(a.project)
    src = Path(a.file).expanduser().resolve()
    if not src.is_file():
        sys.exit(f"not a file: {src}")
    dst = inside(root, "sources/" + src.name)
    if dst.exists():
        sys.exit(f"{dst.name} already in sources; rename the file first")
    rec_p = inside(root, "project-record.json")
    rec = json.loads(rec_p.read_text())
    shutil.copy2(src, dst)
    if dst.is_symlink():
        dst.unlink(); sys.exit("refused: result would be a link")
    rec["sourcesLog"].append({"file": dst.name, "sha256": sha256(dst), "from": str(src), "on": datetime.datetime.now().isoformat(timespec="seconds")})
    rec_p.write_text(json.dumps(rec, indent=2))
    print(f"Copied {src.name} -> sources/ ({sha256(dst)[:12]})")

def cmd_serve(a):
    root = project_root(a.project)
    out = inside(root, "out")
    if not (root.is_dir() and out.is_dir()):
        sys.exit("project folder or out/ missing; run new-project first")
    cli = cli_path(a.app)
    if not cli.is_file() or sha256(cli) != pin(a.app)["cliSha256"]:
        sys.exit(f"{a.app} CLI missing or changed; run setup")
    args = ["mcp", "--automation-read-root", str(root), "--automation-write-root", str(out)]
    if a.watch:
        sys.exit("--watch is not verified by CLI-only setup. Use the confined headless MCP configuration; a desktop connection needs a separately verified app launch and its own roots.")
    cfg = {"mcpServers": {f"patio-{a.app}": {"command": str(cli), "args": args}}}
    if a.write_config:
        p = inside(root, ".mcp.json")
        p.write_text(json.dumps(cfg, indent=2))
        print(f"Wrote {p} (Claude Code reads it from the project folder).")
        print(f"Codex / other clients: claude-style config above, or:\n  claude mcp add patio-{a.app} -- {cli} {' '.join(args)}")
    elif a.run:
        os.execv(str(cli), [str(cli), *args])
    else:
        print(json.dumps(cfg, indent=2))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("setup"); s.add_argument("--app", default="vectorcraft"); s.set_defaults(f=cmd_setup)
    n = sp.add_parser("new-project"); n.add_argument("path"); n.add_argument("--client"); n.add_argument("--apps", nargs="+", default=["vectorcraft"]); n.add_argument("--release-gate", choices=["none","person"], default="none", help="none (default): deliver directly; person: cut files wait for sign-off"); n.set_defaults(f=cmd_new_project)
    b = sp.add_parser("bring"); b.add_argument("project"); b.add_argument("file"); b.set_defaults(f=cmd_bring)
    v = sp.add_parser("serve"); v.add_argument("project"); v.add_argument("--app", default="vectorcraft"); v.add_argument("--write-config", action="store_true"); v.add_argument("--run", action="store_true"); v.add_argument("--watch", action="store_true"); v.set_defaults(f=cmd_serve)
    a = ap.parse_args()
    try:
        a.f(a)
    except ValueError as exc:
        sys.exit(str(exc))

if __name__ == "__main__":
    main()
