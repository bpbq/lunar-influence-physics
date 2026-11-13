#!/usr/bin/env python3
"""Fail on private-repository references, local paths, or broken local links."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".cff", ".sh"}
FORBIDDEN = (
    re.compile(r"github\.com/bpbq/lipe", re.I),
    re.compile(r"/(?:home|Users|workspace)/[A-Za-z0-9_.-]+/"),
    re.compile(r"(?:^|\W)(?:ghp|github_pat)_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bPNAS\b|mean_Total_C|Data S4", re.I),
    re.compile(r"\bsleep\b|physiolog|biolog|human health|human behavio", re.I),
)
LINK = re.compile(r"\[[^]]*]\(([^)]+)\)")


def text_files():
    for path in ROOT.rglob("*"):
        if (path.is_file() and ".git" not in path.parts
                and path.name != "check_public_snapshot.py"
                and path.suffix in TEXT_SUFFIXES):
            yield path


def main():
    failures = []
    for path in text_files():
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            if pattern.search(text):
                failures.append(f"{path.relative_to(ROOT)}: forbidden pattern {pattern.pattern}")
        if path.suffix == ".md":
            for target in LINK.findall(text):
                target = target.split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                if not (path.parent / target).resolve().exists():
                    failures.append(f"{path.relative_to(ROOT)}: broken local link {target}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("public snapshot checks passed")


if __name__ == "__main__":
    main()
