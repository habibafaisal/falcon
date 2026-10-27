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
done < <(find "$src" -type f -not -path "*/__pycache__/*" -print0)

chmod +x "$dest"/.claude/hooks/*.py 2>/dev/null || true
echo "Falcon: copied $copied files into $dest"
if [ ${#skipped[@]} -gt 0 ]; then
  echo "Skipped (already exist — merge by hand):"
  printf '  %s\n' "${skipped[@]}"
fi
cat <<'NEXT'

Next steps:
  1. Open Claude Code in the repo. It sees the unfinished CLAUDE.md and runs the falcon-setup
     interview (or say "set up falcon"). You choose: name your own triggers, or strike out the
     defaults. It fills CLAUDE.md, .claude/protected_paths.txt, review/falcon.toml, review/GATES.md,
     and records your choices in docs/adr/0001-ownership-tiers.md.
  2. pip install pyyaml   — verify.py needs it (and tomli on Python < 3.11)

  Prefer to do it by hand? Edit those same files directly; the setup skill is optional.
NEXT
