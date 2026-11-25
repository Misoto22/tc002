#!/bin/sh
# Stop hook (.claude/settings.json): before Claude ends a turn, check the layering
# contract in tests/test_architecture.py (about a second). On a violation, exit 2 hands
# the list to Claude, which then fixes it before stopping. It does so once per stop
# (stop_hook_active): a violation Claude could not fix is shown to you, not looped on.
input=$(cat)
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0
command -v uv >/dev/null 2>&1 || exit 0  # no uv here: nothing to check with
out=$(uv run --quiet pytest -q --tb=short -p no:cacheprovider tests/test_architecture.py 2>&1) && exit 0
case $input in
  *'"stop_hook_active":true'* | *'"stop_hook_active": true'*)
    printf '%s\n' '{"systemMessage": "tc002: tests/test_architecture.py still fails; run `uv run pytest tests/test_architecture.py`"}'
    exit 0
    ;;
esac
{
  echo "tc002's architecture contract (tests/test_architecture.py) fails. Fix the imports"
  echo "below before finishing, or, if the layering should change, change LAYERS on purpose"
  echo "and paste \`uv run python tests/test_architecture.py\` into docs/architecture.md:"
  printf '%s\n' "$out" | grep -E '^E |^FAILED|passed|failed' | head -60
} >&2
exit 2
