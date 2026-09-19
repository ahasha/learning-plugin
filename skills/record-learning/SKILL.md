---
name: record-learning
description: Record a non-obvious gotcha, condition-specific bug, or correction the user has made more than once into the project's scoped rules. Use this at the end of any task where something surprising was discovered, a bug had a subtle cause, or the user corrected your output, and whenever the user says "remember this" or "add this to the rules".
---

# Record a learning

Capture what would have saved you time this session — and nothing else.

## 1. Decide whether it's worth recording

Record it only if it is **non-obvious**: a gotcha someone would hit again, a bug
that only appears under specific conditions, or a correction the user has now
made more than once.

Skip it if:

- It's a one-off that won't recur.
- It's obvious from reading the code.
- It restates something already in `CLAUDE.md`, `AGENTS.md`, or `.claude/rules/`.

When in doubt, skip. An unread rule costs context in every future session.

## 2. Prefer enforcement over prose

If a test, lint rule, type, schema, or assertion could catch the mistake,
propose that change first and say why it beats a note. Write a note only when
enforcement isn't practical, and say in one clause why.

## 3. Pick the destination

| Scope of the learning | Destination |
| --- | --- |
| Specific files or directories | `.claude/rules/<topic>.md` with `paths:` frontmatter |
| Everywhere in the project | One line in the root `CLAUDE.md` (or `AGENTS.md` if there is no `CLAUDE.md`) |
| A multi-step procedure | Propose a new skill instead — don't inline it |

Before creating a file, run `ls .claude/rules` and read any topic file whose
`paths:` overlap. Append to that file rather than adding a near-duplicate.
Create `.claude/rules/` if it doesn't exist.

Keep the root instruction file under 60 lines. If adding a line would push it
over, that's a signal the learning is really path-scoped — move it.

## 4. Write the entry

One bullet per learning: **the rule, then the reason.** The reason is what stops
a future reader from deleting a rule they don't understand.

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API handlers

- Call `assertTenant(ctx)` before any query in a handler. The ORM's default
  scope is global, so a missing call silently reads across tenants.
```

## 5. Check the `paths:` patterns

- Patterns are globs relative to the project root: `**/*.ts`, `src/**/*`,
  `src/components/*.tsx`.
- Brace expansion works (`src/**/*.{ts,tsx}`), but each brace group multiplies
  the pattern count against a 1,000-pattern budget shared by the whole `paths:`
  list. Keep groups small, or list patterns separately.
- A `[` that isn't a valid bracket expression makes that pattern match nothing.
  Escape a literal bracket as `\[`.
- A rule with no `paths:` loads in **every** session. Only omit `paths:`
  deliberately.

## 6. Verify

Run the check script from the project root:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-rules.py"
```

Fix anything it reports as `error:`. Read the warnings and fix them unless the
warning describes a deliberate choice.

## 7. Show the diff

Show the user the diff for the files you touched. Keep these edits out of
unrelated commits — the point is that the user can review learnings on their
own.
