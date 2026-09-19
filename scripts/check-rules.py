#!/usr/bin/env python3
"""Check a project's .claude/rules/ files and root instruction file.

Run from a project root (or pass the root as the first argument).

Errors (exit 1):
  - the root instruction file is over the line limit
  - a rule's `paths:` patterns match no files (stale rule)
  - a `paths:` pattern is malformed and can silently match nothing

Warnings (exit 0):
  - a rule file has no `paths:` frontmatter, so it loads every session
  - a rule file has empty or unparseable frontmatter
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT_FILES = ("CLAUDE.md", "AGENTS.md", ".claude/CLAUDE.md")
ROOT_LINE_LIMIT = 60
BRACE_BUDGET = 1000
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".tox", ".mypy_cache"}

FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", re.S)
BRACE = re.compile(r"\{([^{}]*)\}")


def frontmatter(text: str) -> str | None:
    """Return the raw frontmatter block, or None if the file has none.

    Claude Code only reads frontmatter when the opening `---` is the very
    first line, so this anchors at the start of the file.
    """
    match = FRONTMATTER.match(text)
    return match.group(1) if match else None


def parse_paths(block: str) -> list[str]:
    """Pull the values of a top-level `paths:` key out of a frontmatter block.

    Handles both the block form:

        paths:
          - "src/**/*.ts"

    and the inline form:

        paths: ["src/**/*.ts", "lib/**"]
    """
    lines = block.splitlines()
    for i, line in enumerate(lines):
        match = re.match(r"^paths:\s*(.*)$", line)
        if not match:
            continue

        inline = match.group(1).strip()
        if inline:
            if inline.startswith("[") and inline.endswith("]"):
                inline = inline[1:-1]
            return [unquote(p) for p in inline.split(",") if unquote(p)]

        values = []
        for item in lines[i + 1 :]:
            if item.strip() and not item.startswith((" ", "\t", "-")):
                break  # next top-level key
            entry = re.match(r"^\s*-\s*(.+?)\s*$", item)
            if entry:
                value = unquote(entry.group(1))
                if value:
                    values.append(value)
        return values
    return []


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value.strip()


def expand_braces(pattern: str, budget: list[int]) -> list[str]:
    """Expand `{a,b}` groups the way Claude Code does, within a budget.

    Claude Code shares one 1,000-pattern budget across a rule's whole `paths:`
    list and uses any pattern that would exceed it unexpanded, where its
    literal braces match nothing. Mirror that so we flag the same stale rules.
    """
    results = [pattern]
    while True:
        grown = []
        changed = False
        for item in results:
            match = BRACE.search(item)
            if not match:
                grown.append(item)
                continue
            changed = True
            head, tail = item[: match.start()], item[match.end() :]
            for option in match.group(1).split(","):
                grown.append(f"{head}{option}{tail}")
        if not changed:
            break
        if len(grown) > budget[0]:
            return [pattern]  # over budget: used unexpanded, braces literal
        results = grown
    budget[0] -= len(results)
    return results


def malformed(pattern: str) -> str | None:
    """Return a reason if the glob can never match, else None."""
    if not pattern:
        return "empty pattern"
    if pattern.startswith("/"):
        return "absolute path; patterns are relative to the project root"
    # Glob treats `[` as opening a bracket expression. An unclosed one is
    # invalid and matches nothing, silently.
    brackets = braces = 0
    escaped = False
    for char in pattern:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "[":
            brackets += 1
        elif char == "]" and brackets:
            brackets -= 1
        elif char == "{":
            braces += 1
        elif char == "}":
            braces -= 1
            if braces < 0:
                return "unbalanced brace group"
    if brackets:
        return "unclosed '[' bracket expression; matches nothing (escape it as '\\[')"
    if braces:
        return "unbalanced brace group"
    return None


def matches_any(root: pathlib.Path, pattern: str) -> bool:
    try:
        for hit in root.glob(pattern):
            if any(part in SKIP_DIRS for part in hit.relative_to(root).parts):
                continue
            return True
    except (ValueError, IndexError, NotImplementedError, OSError):
        # pathlib rejects some patterns outright; treat as "can't tell".
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", nargs="?", default=".", help="project root (default: current directory)")
    parser.add_argument("--max-root-lines", type=int, default=ROOT_LINE_LIMIT,
                        help=f"line limit for the root instruction file (default: {ROOT_LINE_LIMIT})")
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory")
        return 1

    errors: list[str] = []
    warnings: list[str] = []

    rules_dir = root / ".claude" / "rules"
    rule_files = sorted(p for p in rules_dir.glob("**/*.md") if p.is_file()) if rules_dir.is_dir() else []

    for rule in rule_files:
        name = rule.relative_to(root)
        try:
            text = rule.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{name}: cannot read ({exc})")
            continue

        block = frontmatter(text)
        if block is None:
            warnings.append(f"{name}: no frontmatter, so it loads every session")
            continue

        patterns = parse_paths(block)
        if not patterns:
            warnings.append(f"{name}: no paths frontmatter, so it loads every session")
            continue

        budget = [BRACE_BUDGET]
        matched = False
        for pattern in patterns:
            reason = malformed(pattern)
            if reason:
                errors.append(f"{name}: bad pattern {pattern!r}: {reason}")
                continue
            for expanded in expand_braces(pattern, budget):
                if matches_any(root, expanded):
                    matched = True
                    break
            if matched:
                break

        if not matched and not any(str(name) in e for e in errors):
            joined = ", ".join(repr(p) for p in patterns)
            errors.append(f"{name}: paths match no files (stale?): {joined}")

    for name in ROOT_FILES:
        path = root / name
        if not path.is_file():
            continue
        lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        if lines > args.max_root_lines:
            errors.append(f"{name}: {lines} lines, over the {args.max_root_lines}-line limit")

    for warning in warnings:
        print("warning:", warning)
    for error in errors:
        print("error:", error)

    if not errors and not warnings:
        checked = len(rule_files)
        print(f"ok: {checked} rule file{'s' if checked != 1 else ''} checked, no issues")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
