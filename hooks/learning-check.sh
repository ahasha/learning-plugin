#!/usr/bin/env bash
# Stop hook for the scoped-learnings plugin.
#
# Once per session, and only when code outside .claude/ has uncommitted
# changes, ask Claude to consider recording a learning before it stops.
#
# Every failure path exits 0 without prompting: a hook that prompts when it
# can't also write its marker file would loop.

set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0
command -v git >/dev/null 2>&1 || exit 0

input=$(cat)

field() { printf '%s' "$input" | jq -r --arg k "$1" '.[$k] // empty' 2>/dev/null; }

# Already continuing because of a Stop hook — never chain onto ourselves.
[ "$(field stop_hook_active)" = "true" ] && exit 0

# Only the main agent. Subagents have their own Stop semantics.
[ -n "$(field agent_id)" ] && exit 0

# Nothing was written in plan mode, so there is nothing to reflect on.
[ "$(field permission_mode)" = "plan" ] && exit 0

# Run the git checks against the session's working directory.
cwd=$(field cwd)
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  cd "$cwd" || exit 0
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "$CLAUDE_PROJECT_DIR" ]; then
  cd "$CLAUDE_PROJECT_DIR" || exit 0
fi

# Once per session.
session=$(field session_id)
session=${session//[^A-Za-z0-9_-]/_}
[ -z "$session" ] && exit 0

scratch=$(field scratchpad_dir)
if [ -n "$scratch" ] && [ -d "$scratch" ]; then
  marker="$scratch/.scoped-learnings-checked"
else
  marker="${TMPDIR:-/tmp}/claude-learning-$session"
fi
[ -e "$marker" ] && exit 0

# Only speak up when this session actually touched code.
git rev-parse --git-dir >/dev/null 2>&1 || exit 0
changed=$(git status --porcelain --untracked-files=normal -- . ':(exclude).claude' 2>/dev/null)
[ -z "$changed" ] && exit 0

# Claim the marker before prompting. If we can't, stay quiet.
touch "$marker" 2>/dev/null || exit 0

jq -n '{
  hookSpecificOutput: {
    hookEventName: "Stop",
    additionalContext: "Before stopping: did this session surface a non-obvious gotcha, a bug that only appears under specific conditions, or a correction the user has now made more than once? If so, use the record-learning skill to write it to the right scoped rules file. If not, stop — do not mention this check."
  }
}'
exit 0
