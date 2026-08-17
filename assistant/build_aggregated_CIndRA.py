#!/usr/bin/env python3
"""Regenerate aggregated_CIndRA_markdowns.md from all assistant markdown sources."""

from datetime import date
from pathlib import Path

ASSISTANT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = ASSISTANT_DIR / "aggregated_CIndRA_markdowns.md"

SOURCE_FILES = [
    ASSISTANT_DIR / "CIndRA_role.md",
    ASSISTANT_DIR / "skills" / "site-setup" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "national-rainfall" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "national-temperature" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "sea-level-site-setup" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "trend-analysis" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "anomaly-analysis" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "flood-frequency" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "rankings" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "regional-setup" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "regional-atmosphere" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "tropical-cyclones" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "tropical-cyclones" / "references" / "national.md",
    ASSISTANT_DIR / "skills" / "tropical-cyclones" / "references" / "regional.md",
    ASSISTANT_DIR / "skills" / "regional-sea-level" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "functions-api" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "output-conventions" / "SKILL.md",
    ASSISTANT_DIR / "skills" / "data-sources" / "SKILL.md",
    ASSISTANT_DIR / "README.md",
]


def build() -> Path:
    parts = [
        "# CIndRA — Aggregated Training Material\n",
        f"\nSingle-file concatenation of all CIndRA assistant markdowns. "
        f"Generated on {date.today().isoformat()}. "
        f"Source files live in `assistant/` and `assistant/skills/`; "
        f"regenerate with `python assistant/build_aggregated_CIndRA.py`.\n",
    ]

    for path in SOURCE_FILES:
        rel = path.relative_to(ASSISTANT_DIR.parent).as_posix()
        content = path.read_text().rstrip() + "\n"
        parts.append(f"\n---\n\n<!-- SOURCE: {rel} -->\n\n")
        parts.append(content)

    OUTPUT_FILE.write_text("".join(parts))
    return OUTPUT_FILE


if __name__ == "__main__":
    out = build()
    print(f"Wrote {out} ({out.stat().st_size} bytes, {len(SOURCE_FILES)} sections)")
