# scoped-learnings

A Claude Code plugin that records the things worth remembering about a project —
and keeps them out of the context of every future session.

## The problem

The usual way to make Claude remember something is to add a line to `CLAUDE.md`.
Do that enough times and `CLAUDE.md` is 300 lines of mostly-irrelevant advice
loaded into every session, half of it describing code that no longer exists.

## What this does

- **Scopes learnings to paths.** A gotcha about API handlers goes in
  `.claude/rules/api.md` with `paths: ["src/api/**/*.ts"]`. Claude loads it only
  when it reads a matching file.
- **Keeps the root file small.** Only learnings that genuinely apply everywhere
  go in `CLAUDE.md` / `AGENTS.md`, and a check enforces a 60-line ceiling.
- **Prefers enforcement over prose.** If a test, lint rule, type, or assertion
  could catch the mistake, the skill proposes that instead of a note.
- **Keeps learnings reviewable.** They land in their own diff, not buried in an
  unrelated commit.
- **Prunes on demand.** `/scoped-learnings:prune-learnings` audits every entry
  against the current code and deletes what's stale.

The plugin carries all the machinery. Install it once and it works in every
project — there's no per-project setup. The rules themselves are ordinary files
in your repo, so you commit and review them like any other code.

## Install

```
/plugin marketplace add ahasha/learning-plugin
/plugin install scoped-learnings@claude-learnings
```

## Components

| Component | What it does |
| --- | --- |
| `record-learning` skill | Model-invoked. Writes a learning to the right place. Triggers when something surprising turns up, a bug had a subtle cause, you corrected Claude's output, or you say "remember this". |
| `prune-learnings` skill | You-invoked only (`disable-model-invocation: true`). Audits and trims existing rules. |
| `Stop` hook | Once per session, and only when code outside `.claude/` has uncommitted changes, nudges Claude to consider recording a learning. |
| `check-rules.py` | Flags stale `paths:` patterns, rules that load every session, and an over-long root file. |

## Usage

Recording is automatic — the `record-learning` skill triggers on its own, and
the Stop hook nudges once per session when you've touched code. You can also ask
directly:

> remember that the ORM's default scope is global

Pruning is manual, because it deletes things:

```
/scoped-learnings:prune-learnings
```

Run the check yourself any time, from a project root:

```bash
python3 ~/.claude/plugins/.../scripts/check-rules.py
```

Or, more conveniently, let either skill run it — they resolve the path through
`${CLAUDE_PLUGIN_ROOT}`.

## The check script

```
usage: check-rules.py [-h] [--max-root-lines N] [root]
```

**Errors** (exit 1):

- the root instruction file is over the line limit (default 60)
- a rule's `paths:` patterns match no files — the rule is probably stale
- a `paths:` pattern is malformed in a way that silently matches nothing, such
  as an unclosed `[` or an unbalanced brace group

**Warnings** (exit 0):

- a rule file has no `paths:` frontmatter, so it loads in every session

## Requirements

`jq`, `git`, and `python3` on `PATH`. The hook exits quietly if any is missing.

## Local development

```bash
claude --plugin-dir /path/to/learning-plugin
```

Then `/reload-plugins` after edits.

## License

MIT
