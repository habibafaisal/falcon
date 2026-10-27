#!/usr/bin/env bash
# Install the Falcon harness into a target repo. Never overwrites an existing file — it lists skips.
# Usage: ./install.sh /path/to/your/repo
set -euo pipefail

src="$(cd "$(dirname "$0")/template" && pwd)"
dest="${1:?usage: ./install.sh /path/to/target-repo}"
[ -d "$dest" ] || { echo "no such directory: $dest" >&2; exit 1; }

copied=0; skipped=()
while IFS= read -r -d '' f; do
  rel="${f#"$src"/}"
  if [ -e "$dest/$rel" ]; then skipped+=("$rel"); continue; fi
  mkdir -p "$dest/$(dirname "$rel")"
  cp "$f" "$dest/$rel"
  copied=$((copied + 1))
done < <(find "$src" -type f -print0)

chmod +x "$dest"/.claude/hooks/*.py 2>/dev/null || true
echo "Falcon: copied $copied files into $dest"
if [ ${#skipped[@]} -gt 0 ]; then
  echo "Skipped (already exist — merge by hand):"
  printf '  %s\n' "${skipped[@]}"
fi
cat <<'NEXT'

Next steps:
  1. CLAUDE.md            — fill in the project lines and adapt the ownership table to your domain
  2. .claude/protected_paths.txt — list your money/identity/audit paths, each with its invalidation
  3. review/falcon.toml   — set source_dir and test_command
  4. review/GATES.md      — name your single source of truth under "Intent sources"
  5. pip install pyyaml   — verify.py needs it (and tomli on Python < 3.11)
NEXT
