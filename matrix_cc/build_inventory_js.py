#!/usr/bin/env python3
"""Build inventory.js: the automatic part of the CIndRA product records shown in the matrix.

For every product file (figures, interactive HTML, CSV tables) under the given directories it stores the
run date (file modification time), size and SHA-256; for every CSV also its columns, number of rows and the
period covered (first/last year found in a year/date column). It also records the code version of the
repository (git commit, branch, uncommitted changes) and the local-copy date of the source data files, so
index.html can assemble the provenance and validation sections of each product record.

The hand-written part of each record (methods, limitations, sources, review status) lives in records.js.

Usage:  python3 build_inventory_js.py <index_dir> <product_dir> [<product_dir> ...] [--data <data_dir>]

Paths are relative to <index_dir> (the folder holding index.html) and keys are stored exactly as products.js
resolves them (e.g. '../outputs/figures/<station>/F2_ST_Mean_<station>.png').

  python3 build_inventory_js.py . figures ../outputs/figures ../outputs/tables ../notebooks/matrix_cc/figures --data ../data
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PRODUCT_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".html", ".csv", ".json"}
DATA_SUFFIXES = {".pkl", ".nc", ".txt", ".csv", ".json", ".zarr"}
YEAR_RE = re.compile(r"(1[89]\d\d|20\d\d|21\d\d)")


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_summary(path: Path) -> dict:
    """Columns, data rows and period (first/last year of a year/date column, else of the first column)."""
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))
    if not rows:
        return {"columns": [], "rows": 0}
    head, body = rows[0], [r for r in rows[1:] if any(c.strip() for c in r)]
    out = {"columns": head, "rows": len(body)}
    cands = [i for i, h in enumerate(head) if re.search(r"year|date|time", h, re.I)] or [0]
    for i in cands:
        years = []
        for r in body:
            m = YEAR_RE.match(r[i].strip()) if i < len(r) else None
            if m:
                years.append(int(m.group(1)))
        if len(years) >= max(2, len(body) // 2):  # mostly year-like values
            out["period"] = [min(years), max(years)]
            break
    return out


def git_info(repo_dir: Path) -> dict:
    def git(*args):
        r = subprocess.run(["git", "-C", str(repo_dir), *args], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""

    commit = git("rev-parse", "HEAD")
    if not commit:
        return {}
    remote = git("remote", "get-url", "origin")
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote)
    return {
        "commit": commit,
        "short": commit[:7],
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "commitDate": git("log", "-1", "--format=%cI"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "remote": f"https://github.com/{m.group(1)}" if m else remote,
    }


def main(index_dir: str, product_dirs: list[str], data_dirs: list[str]) -> None:
    index_dir = Path(index_dir).resolve()
    rel = lambda p: Path(os.path.relpath(p, index_dir)).as_posix()

    files, tables = {}, {}
    for d in product_dirs:
        root = (index_dir / d).resolve()
        if not root.is_dir():
            print(f"Warning: {root} not found, skipped", file=sys.stderr)
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in PRODUCT_SUFFIXES:
                continue
            st = p.stat()
            key = rel(p)
            files[key] = {"modified": iso(st.st_mtime), "size": st.st_size, "sha256": sha256(p)}
            if p.suffix.lower() == ".csv":
                tables[key] = csv_summary(p)

    data = {}
    for d in data_dirs:
        root = (index_dir / d).resolve()
        if not root.is_dir():
            print(f"Warning: {root} not found, skipped", file=sys.stderr)
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix.lower() in DATA_SUFFIXES:
                st = p.stat()
                data[rel(p)] = {"modified": iso(st.st_mtime), "size": st.st_size}

    inventory = {
        "generated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "repo": git_info(index_dir),
        "files": files,
        "tables": tables,
        "data": data,
    }
    out = index_dir / "inventory.js"
    out.write_text(
        "// Generated by build_inventory_js.py -- automatic part of the product records. Do not edit.\n"
        "window.CINDRA_INVENTORY = " + json.dumps(inventory, ensure_ascii=False, indent=0) + ";\n",
        encoding="utf-8",
    )
    print(f"Inventory: {len(files)} product files ({len(tables)} tables), {len(data)} data files, "
          f"commit {inventory['repo'].get('short', '?')}{' (uncommitted changes)' if inventory['repo'].get('dirty') else ''} "
          f"-> {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    data_dirs = []
    while "--data" in args:
        i = args.index("--data")
        data_dirs.append(args[i + 1])
        del args[i:i + 2]
    main(args[0], args[1:], data_dirs)
