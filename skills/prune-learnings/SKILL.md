---
name: prune-learnings
description: Audit and trim the project's learned rules and root instruction file.
disable-model-invocation: true
---

# Prune learnings

A maintenance pass over `.claude/rules/` and the root instruction file. Run it
from the project root. Nothing here is automatic — produce a diff and let the
user decide.

## 1. Run the check script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-rules.py"
```

Fix every `error:`. Triage each `warning:`.

## 2. Test each entry against the current code

Read every bullet in `.claude/rules/**/*.md` and in the root `CLAUDE.md` /
`AGENTS.md`. For each one, find the code it describes.

- The code is gone, or no longer works that way → **delete the entry.**
- The code changed but the hazard remains → **rewrite the entry** to match.
- You can't tell → leave it and list it for the user under "couldn't verify".

Don't preserve an entry just because deleting feels lossy. A stale rule is worse
than no rule: it is confidently wrong.

## 3. Merge duplicates

Collapse entries that say the same thing, and entries whose `paths:` overlap and
whose topics are the same. Prefer one file per topic with a wider `paths:` list
over several files with near-identical patterns.

## 4. Propose enforcement for recurring mistakes

For each entry that describes a mistake someone keeps making, propose the test,
lint rule, type, or assertion that would make the note unnecessary — then delete
the note in the same diff if the user accepts.

## 5. Re-scope over-broad entries

- A root-file line that only applies to certain paths → move it into
  `.claude/rules/<topic>.md` with `paths:`.
- A rule file with no `paths:` that clearly applies to a subset → add `paths:`.
- Root file over 60 lines → move the most path-specific lines out until it fits.

## 6. Show the full diff

Print the complete diff and a short summary: how many entries were deleted,
merged, re-scoped, and how many you couldn't verify. Don't commit unless the
user asks.
