"""Deterministic layer of the Falcon review harness.

Runs the machine-checkable pass over review/capabilities/*.md:

  1. frontmatter schema (vocab pinned below, mirrors GATES.md)
  2. evidence paths exist in-repo (absolute / /tmp paths rejected)
  3. governing tests actually run, counts reported with skips split out
  4. same-origin evidence flag (test + cited source code introduced in one commit)
  5. `executed:` stamp — this script is the ONLY writer of that field
  6. hazard scans from review/HAZARDS.md (backticked detection commands; output = hazard present)

  --map  runs the MAP FRESHNESS pass instead (added 2026-09-13, closes the M8 hole — prose-vs-code
         drift was invisible to this gate):
           a. every backticked repo path cited in the canonical docs exists
              (a line marked deleted/retired/moved/was/as-of-filing is provenance and exempt)
           b. every package dir under the source dir has a row in ARCHITECTURE.md
           c. every module under the source dir is named somewhere in ARCHITECTURE.md (WARN)
           d. the source dir has not moved far ahead of ARCHITECTURE.md's last commit (WARN)

  --plans  runs the PLAN GATE instead: every changed file (vs HEAD, plus untracked) that matches
           .claude/protected_paths.txt must be covered by a RATIFIED plan in docs/plans/ that lists
           it (or its directory) under `protected_paths:`. A proposed plan does not count. Plans are
           optional for delegated work, so unprotected changes are never checked.

Repo-specific settings (source dir, test command, canonical docs) live in review/falcon.toml.

Exit 0 if no FAILs (WARNs allowed), 1 otherwise.
Usage: python review/verify.py [capability-slug ...]
       python review/verify.py --map
       python review/verify.py --plans
       python review/verify.py --no-stamp [slug ...]   (read-only: skip the executed: stamp; git pre-commit uses it)
"""

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # PyYAML missing — refuse, don't guess
    # PyYAML is a declared dependency and present under uv. An audit gatekeeper that can't
    # fully parse its input must FAIL LOUD, never silently degrade to a lossy parser and still
    # print [PASS] — that once hid an unvalidated scenario block behind green checks.
    sys.exit(
        "review/verify.py requires PyYAML but it is not importable.\n"
        "    Install it in the project env (e.g. `uv add --dev pyyaml` or `pip install pyyaml`).\n"
    )

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES_DIR = REPO_ROOT / "review" / "capabilities"
HAZARDS_PATH = REPO_ROOT / "review" / "HAZARDS.md"
CONFIG_PATH = REPO_ROOT / "review" / "falcon.toml"
PROTECTED_PATHS_FILE = REPO_ROOT / ".claude" / "protected_paths.txt"
PLANS_DIR = REPO_ROOT / "docs" / "plans"


def load_config(path=CONFIG_PATH):
    """Repo-specific settings. Missing file or key -> the default below; a malformed file fails loud."""
    cfg = {
        "source_dir": "app",
        "test_command": ["python", "-m", "pytest"],
        "map_docs": ["ARCHITECTURE.md", "CLAUDE.md", "INVARIANTS.md", "docs/working_rules.md",
                     "review/GATES.md", "review/HAZARDS.md", "review/SCENARIOS.md",
                     ".claude/agents/oracle.md"],
        "map_drift_commits": 15,
    }
    if path.exists():
        try:
            import tomllib
        except ModuleNotFoundError:  # Python < 3.11
            import tomli as tomllib  # fail loud if absent: a config we can't read must not be ignored
        with open(path, "rb") as fh:
            cfg.update(tomllib.load(fh))
    return cfg


CONFIG = load_config()
SOURCE_DIR = str(CONFIG["source_dir"]).rstrip("/")

CAPABILITY_STATES = {
    "not_started", "implemented", "integrated", "exercised", "validated", "operational",
}
PERMITTED_USES = {
    "prototype_only", "demo_only", "historical_backtest", "shadow_mode",
    "human_approved_live", "automated_live",
}
SCENARIO_STATUSES = {"demonstrated", "inferred", "contradicted", "unverified"}
# red_ability — did a MUTATION SWEEP prove this capability's own tests catch the guard being
# removed? `proven` = a documented mutation flipped the real guard and the suite went RED (evidence
# class 3). `unproven` = no sweep run yet (green may be untrusted-green). `not_applicable` = the
# capability has no single mechanical guard to mutate. This field is OPTIONAL; it certifies the test
# suite's teeth, not the code. Only the review-harness mutation-sweep mode should set/refresh it.
RED_ABILITY_STATUSES = {"proven", "unproven", "not_applicable"}
# review_log — OPTIONAL. One entry per completed fresh-reviewer verdict, so a later review can see
# which scenarios were already judged against which commit. Never load-bearing for state/use.
REVIEW_LOG_VERDICTS = SCENARIO_STATUSES
REQUIRED_KEYS = {
    "capability", "capability_state", "permitted_use", "authority",
    "governing_tests", "scenarios", "evidence_class", "executed",
}

PASS, FAIL, WARN, SKIP = "PASS", "FAIL", "WARN", "SKIP"


class Finding:
    """One check result: (check name, PASS/FAIL/WARN, reason)."""

    def __init__(self, check, status, reason):
        self.check = check
        self.status = status
        self.reason = reason


# ---------------------------------------------------------------------------
# Check 1 — frontmatter parse + schema
# ---------------------------------------------------------------------------

def parse_frontmatter(text):
    """Return (frontmatter dict, error string). Frontmatter sits between --- fences."""
    m = re.match(r"\A---\s*\n(.*?)\n---\s*(\n|\Z)", text, re.DOTALL)
    if not m:
        return None, "no frontmatter fences (--- ... ---) found"
    try:
        data = yaml.safe_load(m.group(1))
    except Exception as exc:  # yaml.YAMLError — report, don't crash
        return None, f"YAML parse error: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter is not a YAML mapping"
    return data, None


def check_schema(fm):
    """Validate the pinned frontmatter schema. Returns a list of error strings."""
    errors = []
    missing = REQUIRED_KEYS - set(fm)
    if missing:
        errors.append(f"missing required keys: {', '.join(sorted(missing))}")

    if "capability_state" in fm and fm["capability_state"] not in CAPABILITY_STATES:
        errors.append(f"capability_state {fm['capability_state']!r} not in {sorted(CAPABILITY_STATES)}")
    if "permitted_use" in fm and fm["permitted_use"] not in PERMITTED_USES:
        errors.append(f"permitted_use {fm['permitted_use']!r} not in {sorted(PERMITTED_USES)}")

    authority = fm.get("authority")
    if authority is not None:
        if not isinstance(authority, list):
            errors.append("authority must be a list of {source, pointer}")
        else:
            for i, entry in enumerate(authority):
                if not isinstance(entry, dict) or "source" not in entry or "pointer" not in entry:
                    errors.append(f"authority[{i}] must have 'source' and 'pointer' (a locator to re-read live, never a copied quote)")

    tests = fm.get("governing_tests")
    if tests is not None and (
        not isinstance(tests, list) or not all(isinstance(t, str) for t in tests)
    ):
        errors.append("governing_tests must be a list of paths")

    scenarios = fm.get("scenarios")
    if scenarios is not None:
        if not isinstance(scenarios, dict):
            errors.append("scenarios must be a map of S# -> {status, evidence, concern}")
        else:
            for key, entry in scenarios.items():
                if not re.fullmatch(r"S\d+", str(key)):
                    errors.append(f"scenario key {key!r} is not of the form S#")
                if not isinstance(entry, dict):
                    errors.append(f"scenario {key} must be a mapping")
                    continue
                status = entry.get("status")
                if status not in SCENARIO_STATUSES:
                    errors.append(f"scenario {key} status {status!r} not in {sorted(SCENARIO_STATUSES)}")

    ec = fm.get("evidence_class")
    if ec is not None and (not isinstance(ec, int) or not 0 <= ec <= 5):
        errors.append(f"evidence_class {ec!r} must be an integer 0-5")

    # red_ability is OPTIONAL, but if present it must be a well-formed sweep record: a status from
    # the vocabulary, and — when `proven` — the mutation that was applied and when it last ran, so the
    # claim "our tests catch the guard's removal" is auditable, not asserted.
    ra = fm.get("red_ability")
    if ra is not None:
        if not isinstance(ra, dict):
            errors.append("red_ability must be a mapping of {status, last_swept, mutation}")
        else:
            status = ra.get("status")
            if status not in RED_ABILITY_STATUSES:
                errors.append(f"red_ability status {status!r} not in {sorted(RED_ABILITY_STATUSES)}")
            if status == "proven":
                for req in ("last_swept", "mutation"):
                    if not ra.get(req):
                        errors.append(f"red_ability status 'proven' requires a non-empty {req!r}")

    # review_log is OPTIONAL. If present, each entry must say which scenario, which commit it was
    # reviewed against, when, and what the verdict was — enough to judge whether it still holds.
    rl = fm.get("review_log")
    if rl is not None:
        if not isinstance(rl, list):
            errors.append("review_log must be a list of {scenario, reviewed_commit, reviewed_at, verdict}")
        else:
            scenario_keys = set(scenarios) if isinstance(scenarios, dict) else set()
            for i, entry in enumerate(rl):
                if not isinstance(entry, dict):
                    errors.append(f"review_log[{i}] must be a mapping")
                    continue
                for req in ("scenario", "reviewed_commit", "reviewed_at", "verdict"):
                    if not entry.get(req):
                        errors.append(f"review_log[{i}] missing non-empty {req!r}")
                scen_id = entry.get("scenario")
                if scen_id and scenario_keys and scen_id not in scenario_keys:
                    errors.append(f"review_log[{i}] scenario {scen_id!r} is not a key in scenarios")
                verdict = entry.get("verdict")
                if verdict is not None and verdict not in REVIEW_LOG_VERDICTS:
                    errors.append(f"review_log[{i}] verdict {verdict!r} not in {sorted(REVIEW_LOG_VERDICTS)}")

    return errors


# ---------------------------------------------------------------------------
# Check 2 — evidence paths exist in-repo
# ---------------------------------------------------------------------------

def collect_evidence_paths(fm):
    """All paths a capability file cites: authority sources, governing tests, scenario evidence."""
    paths = []
    for entry in fm.get("authority") or []:
        if isinstance(entry, dict) and entry.get("source"):
            paths.append(str(entry["source"]))
    for t in fm.get("governing_tests") or []:
        paths.append(str(t))
    scenarios = fm.get("scenarios") or {}
    if isinstance(scenarios, dict):
        for entry in scenarios.values():
            if isinstance(entry, dict) and entry.get("evidence"):
                ev = entry["evidence"]
                # evidence may be a single path OR a list of paths — a scenario can be governed
                # by more than one test (e.g. a canon test + an independent regression). Normalize
                # to individual paths so each is existence-checked; a list must NOT be str()'d whole
                # (that yields a bogus "['a', 'b']" path that fails the in-repo check).
                paths.extend(str(e) for e in (ev if isinstance(ev, list) else [ev]))
    return paths


# A leading `<repo>:` prefix (an alphanumeric/underscore repo token, then `:`, then a
# path) marks CROSS-REPO evidence — it lives in another repo (e.g. `FE:src/foo.tsx`) and is
# un-runnable from here, so it is existence-EXEMPT. The negative lookahead `(?!\d)` keeps a
# normal `path:12` line-anchor (digits after the `:`) from being mistaken for a repo prefix.
_CROSS_REPO_PREFIX = re.compile(r"\A[A-Za-z_]\w*:(?!\d)")


def is_cross_repo_evidence(p):
    """True if p is a `<repo>:path` cross-repo reference, not a `path:linenumber` anchor."""
    return bool(_CROSS_REPO_PREFIX.match(p))


def check_evidence_paths(paths, repo_root):
    """Returns (errors, warnings). Absolute or /tmp paths are rejected outright; cross-repo
    references are existence-exempt and reported as warnings (un-runnable from here)."""
    errors, warnings = [], []
    for p in paths:
        if is_cross_repo_evidence(p):
            warnings.append(f"{p}: cross-repo evidence, un-runnable from here")
            continue
        # Evidence may cite a line/anchor suffix (path#L10 or path:12) — strip it.
        bare = re.split(r"[#:]", p, maxsplit=1)[0]
        if bare.startswith("/") or bare.startswith("~"):
            errors.append(f"{p}: absolute path — evidence must live in the repo")
        elif not (Path(repo_root) / bare).exists():
            errors.append(f"{p}: does not exist in repo")
    return errors, warnings


# ---------------------------------------------------------------------------
# Check 3 — run governing tests, report exact counts
# ---------------------------------------------------------------------------

_SUMMARY_TOKEN = re.compile(r"(\d+)\s+(passed|skipped|failed|errors?|error|xfailed|xpassed|warnings?|deselected)")


def parse_pytest_summary(output):
    """Parse a pytest run's output into exact counts.

    Returns {"passed": X, "skipped": Y, "failed": Z, "errors": W} from the final
    summary line, or None if no summary line is found.
    """
    counts = None
    for line in output.splitlines():
        if not re.search(r"\d+\s+(passed|failed|error|skipped|xfailed|xpassed)", line):
            continue
        found = {"passed": 0, "skipped": 0, "failed": 0, "errors": 0}
        for num, word in _SUMMARY_TOKEN.findall(line):
            if word.startswith("error"):
                found["errors"] += int(num)
            elif word in ("passed", "skipped", "failed"):
                found[word] = int(num)
        counts = found  # keep the last matching line — pytest's summary is final
    return counts


def run_governing_tests(test_paths, repo_root):
    """Run `<test_command> <paths> -q` (from falcon.toml) and return a Finding."""
    if not test_paths:
        return Finding("tests", WARN, "no governing_tests listed")
    try:
        proc = subprocess.run(
            [*CONFIG["test_command"], *test_paths, "-q"],
            cwd=repo_root, capture_output=True, text=True, timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Finding("tests", WARN, f"pytest could not run: {exc}")

    output = proc.stdout + proc.stderr
    counts = parse_pytest_summary(output)
    if counts is None:
        tail = "\n".join(output.splitlines()[-10:])
        return Finding("tests", WARN, f"could not parse pytest summary; raw tail:\n{tail}")

    detail = (
        f"{counts['passed']} passed, {counts['skipped']} skipped, "
        f"{counts['failed']} failed, {counts['errors']} errors"
    )
    if counts["failed"] or counts["errors"]:
        return Finding("tests", FAIL, detail)
    return Finding("tests", PASS, detail)


# ---------------------------------------------------------------------------
# Check 4 — same-origin evidence flag
# ---------------------------------------------------------------------------

def introducing_commit(path, repo_root):
    """Oldest commit touching path per `git log --follow`, or None."""
    try:
        proc = subprocess.run(
            ["git", "log", "--follow", "--format=%H", "--", path],
            cwd=repo_root, capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = proc.stdout.split()
    return lines[-1] if lines else None


def check_same_origin(fm, repo_root, get_intro=introducing_commit, source_dir=None):
    """WARN if a governing test and a cited source file were introduced in the same commit."""
    prefix = (source_dir or SOURCE_DIR) + "/"
    app_sources = [
        str(e["source"]) for e in (fm.get("authority") or [])
        if isinstance(e, dict) and str(e.get("source", "")).startswith(prefix)
    ]
    tests = [str(t) for t in (fm.get("governing_tests") or [])]
    if not app_sources or not tests:
        return []
    warnings = []
    app_intros = {src: get_intro(src, repo_root) for src in app_sources}
    for test in tests:
        t_intro = get_intro(test, repo_root)
        if t_intro is None:
            continue
        for src, s_intro in app_intros.items():
            if s_intro is not None and s_intro == t_intro:
                warnings.append(
                    f"same-origin evidence (class >=4): {test} and {src} "
                    f"introduced in commit {t_intro[:12]}"
                )
    return warnings


# ---------------------------------------------------------------------------
# Check 5 — executed stamp (this script is the only writer)
# ---------------------------------------------------------------------------

def stamp_executed(text, timestamp, outcome):
    """Rewrite ONLY the `executed:` line inside the frontmatter block.

    `outcome` (PASS|FAIL) is written into the stamp so a failing capability can never read
    as green — a bare timestamp was treated as a clean marker and masked real schema FAILs
    (examples/case-studies/CASE-05). Everything else is preserved byte-for-byte. Returns the new text, or None
    if no `executed:` line exists in the frontmatter.
    """
    m = re.match(r"\A(---\s*\n)(.*?)(\n---)", text, re.DOTALL)
    if not m:
        return None
    body = m.group(2)
    new_body, n = re.subn(
        r"^executed:.*$",
        f'executed: "{timestamp} verify.py {outcome}"',
        body, count=1, flags=re.MULTILINE,
    )
    if n == 0:
        return None
    return text[: m.start(2)] + new_body + text[m.end(2):]


# ---------------------------------------------------------------------------
# Check 6 — hazard scans from review/HAZARDS.md
# ---------------------------------------------------------------------------

_LEADING_BACKTICK_CMD = re.compile(r"`([^`]+)`")  # used with .match: the backtick must LEAD the cell


def parse_hazard_rows(md_text):
    """Extract (hazard_id, detection command) from HAZARDS.md table rows.

    A row is a RUNNABLE check only when one of its cells LEADS with a backticked command
    (optionally followed by an annotation: `cmd` (why)). A backtick buried mid-prose is a
    filename or word being *discussed*, not a command to execute — running it produced empty
    stdout that the gatekeeper wrongly certified as [PASS] clean (see examples/case-studies/CASE-05). Rows with no leading-backtick command are review-reads:
    returned in `skipped`, surfaced to a human, never silently passed.
    Convention: a detection command OUTPUTS MATCHES when the hazard is present.
    """
    rows, skipped = [], []
    for line in md_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        first = cells[0]
        # Skip header/separator rows.
        if set(first) <= {"-", ":", " "} or first.lower() in ("id", "hazard", "hazard id"):
            continue
        cmd = None
        for cell in cells[1:]:
            m = _LEADING_BACKTICK_CMD.match(cell)  # anchored: the command must LEAD the cell
            if m:
                cmd = m.group(1)
                break
        if cmd:
            rows.append((first, cmd))
        else:
            skipped.append(first)
    return rows, skipped


def run_hazard_scans(repo_root):
    """Run every mechanical detection in HAZARDS.md. Returns a list of Findings."""
    if not HAZARDS_PATH.exists():
        return [Finding("hazards", PASS, "review/HAZARDS.md not present yet — skipped")]
    rows, skipped = parse_hazard_rows(HAZARDS_PATH.read_text())
    findings = []
    for hid in skipped:
        # A review-read is NOT clean — it is un-checked. Say so; never print [PASS].
        findings.append(Finding("hazards", SKIP, f"{hid}: review-read — a human must check this, NOT auto-verified"))
    for hid, cmd in rows:
        try:
            proc = subprocess.run(
                cmd, shell=True, cwd=repo_root, capture_output=True, text=True, timeout=30,
            )
        except subprocess.TimeoutExpired:
            findings.append(Finding("hazards", WARN, f"{hid}: detection timed out (30s): {cmd}"))
            continue
        out = proc.stdout.strip()
        if out:
            head = "\n    ".join(out.splitlines()[:5])
            findings.append(Finding("hazards", WARN, f"{hid}: hazard present —\n    {head}"))
        else:
            findings.append(Finding("hazards", PASS, f"{hid}: clean"))
    return findings


# ---------------------------------------------------------------------------
# Check 7 — map freshness (--map): the canonical docs must describe the code that exists
# ---------------------------------------------------------------------------

# The docs the `oracle` agent and CLAUDE.md treat as canonical (set in falcon.toml). Historical logs
# (docs/mistakes.md, review/escapes/) are NOT canonical on purpose: their citations are as-of-filing
# provenance and must not be "fixed".
MAP_DOCS = list(CONFIG["map_docs"])
_CITED_PATH = re.compile(
    r"`((?:" + re.escape(SOURCE_DIR) + r"|tests|scripts|review|docs|plan|migrations|config)/"
    r"[A-Za-z0-9_./\-]+?\.(?:py|md|yaml|yml|json|sh|toml|ini|txt))(?::[\d,\-]+)?(?:::[A-Za-z_][A-Za-z0-9_]*)?`"
)
# A citation on a line carrying one of these words is provenance ("moved from X", "was `X`",
# "deleted `X`"), not a claim that X exists now.
_PROVENANCE_WORDS = ("deleted", "retired", "moved", "was `", "as-of-filing", "previously", "superseded", "renamed")
MAP_DRIFT_COMMITS = int(CONFIG["map_drift_commits"])  # source commits since ARCHITECTURE.md changed before we WARN


def check_map_freshness(repo_root):
    """Return a list of Findings for the map-freshness pass."""
    findings = []
    arch_path = repo_root / "ARCHITECTURE.md"
    arch_text = arch_path.read_text() if arch_path.exists() else ""

    # (a) path liveness
    dead = {}
    for rel in MAP_DOCS:
        p = repo_root / rel
        if not p.exists():
            findings.append(Finding("map", WARN, f"canonical doc missing: {rel}"))
            continue
        for line in p.read_text().splitlines():
            low = line.lower()
            if any(w in low for w in _PROVENANCE_WORDS):
                continue
            for m in _CITED_PATH.finditer(line):
                cited = m.group(1)
                if not (repo_root / cited).exists():
                    dead.setdefault(cited, set()).add(rel)
    if dead:
        for cited, where in sorted(dead.items()):
            findings.append(Finding("map", FAIL, f"dead path `{cited}` cited in {', '.join(sorted(where))}"))
    else:
        findings.append(Finding("map", PASS, f"every cited path in {len(MAP_DOCS)} canonical docs exists"))

    # (b) package coverage
    if not arch_text:
        findings.append(Finding("map", FAIL, "ARCHITECTURE.md missing — the map does not exist"))
        return findings
    app_dir = repo_root / SOURCE_DIR
    if not app_dir.is_dir():
        findings.append(Finding("map", WARN, f"source dir {SOURCE_DIR}/ not found — set source_dir in review/falcon.toml"))
        return findings
    packages = sorted(
        d for d in app_dir.iterdir()
        if d.is_dir() and d.name != "__pycache__" and (d / "__init__.py").exists()
    )
    undocumented = [d.name for d in packages if f"`{SOURCE_DIR}/{d.name}/`" not in arch_text]
    if undocumented:
        findings.append(Finding("map", FAIL, f"{SOURCE_DIR}/ packages with no row in ARCHITECTURE.md: {', '.join(undocumented)}"))
    else:
        findings.append(Finding("map", PASS, f"all {len(packages)} {SOURCE_DIR}/ packages have a row in ARCHITECTURE.md"))

    # (c) module coverage (WARN — routers are listed by name in prose, so match on the bare stem)
    unnamed = []
    globs = set(re.findall(r"`?([A-Za-z0-9_]+)_\*`?", arch_text))  # `foo_*` names every foo_… module
    for py in sorted(app_dir.rglob("*.py")):
        if "__pycache__" in py.parts or py.name == "__init__.py":
            continue
        named = py.name in arch_text or py.stem in arch_text or any(py.stem.startswith(g + "_") for g in globs)
        if not named:
            unnamed.append(str(py.relative_to(repo_root)))
    if unnamed:
        head = ", ".join(unnamed[:12]) + (" …" if len(unnamed) > 12 else "")
        findings.append(Finding("map", WARN, f"{len(unnamed)} {SOURCE_DIR}/ modules not named in ARCHITECTURE.md: {head}"))
    else:
        findings.append(Finding("map", PASS, f"every {SOURCE_DIR}/ module is named in ARCHITECTURE.md"))

    # (d) freshness watermark
    try:
        last_arch = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", "ARCHITECTURE.md"],
            cwd=repo_root, capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        if last_arch:
            since = subprocess.run(
                ["git", "rev-list", "--count", f"{last_arch}..HEAD", "--", SOURCE_DIR + "/"],
                cwd=repo_root, capture_output=True, text=True, timeout=30,
            ).stdout.strip()
            n = int(since or 0)
            if n > MAP_DRIFT_COMMITS:
                findings.append(Finding("map", WARN, f"{n} commits touched {SOURCE_DIR}/ since ARCHITECTURE.md last changed (> {MAP_DRIFT_COMMITS}) — re-read the map against the code"))
            else:
                findings.append(Finding("map", PASS, f"{n} commits touched {SOURCE_DIR}/ since ARCHITECTURE.md last changed"))
    except (subprocess.SubprocessError, ValueError, OSError) as e:  # git unavailable — say so, never PASS
        findings.append(Finding("map", SKIP, f"freshness watermark not computed: {e}"))
    return findings


def run_map(repo_root):
    print("== map freshness (--map) ==")
    worst = PASS
    for f in check_map_freshness(repo_root):
        print(f"  [{f.status}] {f.reason}")
        if f.status == FAIL:
            worst = FAIL
    print()
    return 1 if worst == FAIL else 0


# ---------------------------------------------------------------------------
# Check 8 — plan gate (--plans): no UNDERSTAND-IT change without a ratified plan
# ---------------------------------------------------------------------------

def load_protected_entries(path=PROTECTED_PATHS_FILE):
    """Entries from protected_paths.txt (same format the fence hook reads). Missing file -> none."""
    if not path.exists():
        return ()
    entries = (line.split("#", 1)[0].strip() for line in path.read_text().splitlines())
    return tuple(e for e in entries if e)


def _path_matches(path, entry):
    """A trailing "/" entry is a directory prefix; anything else is an exact file."""
    return path.startswith(entry) if entry.endswith("/") else path == entry


def load_plans(plans_dir=PLANS_DIR):
    """(plans, errors). Each plan is its frontmatter dict plus `_file`. The template is skipped; a
    plan file whose frontmatter can't be parsed is an ERROR, never silently ignored."""
    plans, errors = [], []
    if not plans_dir.is_dir():
        return plans, errors
    for f in sorted(plans_dir.glob("*.md")):
        if f.name.startswith("0000-") or f.name.lower() == "readme.md":
            continue
        fm, err = parse_frontmatter(f.read_text())
        if fm is None:
            errors.append(f"{f.name}: {err}")
            continue
        fm["_file"] = f"docs/plans/{f.name}"
        plans.append(fm)
    return plans, errors


def check_plans(changed, protected, plans):
    """One Finding per changed protected path: PASS if a ratified plan covers it, FAIL otherwise."""
    findings = []
    for path in changed:
        if not any(_path_matches(path, e) for e in protected):
            continue
        covering = [p for p in plans if any(_path_matches(path, c) for c in (p.get("protected_paths") or []))]
        ratified = [p for p in covering if str(p.get("status", "")).lower() == "ratified"]
        if ratified:
            findings.append(Finding("plans", PASS, f"{path}: covered by {ratified[0]['_file']}"))
        elif covering:
            findings.append(Finding("plans", FAIL, f"{path}: plan {covering[0]['_file']} is "
                                    f"{covering[0].get('status', 'unset')}, not ratified"))
        else:
            findings.append(Finding("plans", FAIL, f"{path}: protected (UNDERSTAND-IT) but no plan in "
                                    "docs/plans/ lists it; write one and get it ratified first"))
    return findings


def changed_paths(repo_root):
    """Files changed vs HEAD plus untracked files. A repo with no commits yet: every file counts."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True, check=True).stdout.split()
    try:
        tracked = git("diff", "--name-only", "HEAD")
    except subprocess.CalledProcessError:  # no HEAD yet
        tracked = git("ls-files", "--cached")
    return sorted(set(tracked) | set(git("ls-files", "--others", "--exclude-standard")))


def run_plans(repo_root):
    print("== plan gate (--plans) ==")
    plans, errors = load_plans(repo_root / "docs" / "plans")
    findings = [Finding("plans", FAIL, e) for e in errors]
    try:
        changed = changed_paths(repo_root)
    except (subprocess.SubprocessError, OSError) as e:  # git unavailable: say so, never PASS
        findings.append(Finding("plans", FAIL, f"could not list changed files: {e}"))
        changed = []
    findings += check_plans(changed, load_protected_entries(repo_root / ".claude" / "protected_paths.txt"), plans)
    if not findings:
        findings.append(Finding("plans", PASS, "no protected paths changed"))
    for f in findings:
        print(f"  [{f.status}] {f.reason}")
    print()
    return 1 if any(f.status == FAIL for f in findings) else 0


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def verify_capability(path, repo_root, stamp=True):
    """Run checks 1-5 on one capability file. Returns (findings, stamped: bool).

    stamp=False (`--no-stamp`) runs checks 1-4 read-only: the git pre-commit gate uses it so the
    commit it guards does not leave the capability file dirty again."""
    findings = []
    text = path.read_text()
    fm, err = parse_frontmatter(text)
    if fm is None:
        findings.append(Finding("frontmatter", FAIL, err))
        return findings, False

    schema_errors = check_schema(fm)
    if schema_errors:
        findings.append(Finding("frontmatter", FAIL, "; ".join(schema_errors)))
    else:
        findings.append(Finding("frontmatter", PASS, "schema valid"))

    path_errors, path_warnings = check_evidence_paths(collect_evidence_paths(fm), repo_root)
    if path_errors:
        findings.append(Finding("evidence-paths", FAIL, "; ".join(path_errors)))
    else:
        findings.append(Finding("evidence-paths", PASS, "all cited in-repo paths exist"))
    for w in path_warnings:
        findings.append(Finding("evidence-paths", WARN, w))

    tests = [str(t) for t in (fm.get("governing_tests") or []) if isinstance(t, str)]
    runnable = [t for t in tests if (Path(repo_root) / t).exists()]
    findings.append(run_governing_tests(runnable, repo_root))

    for w in check_same_origin(fm, repo_root):
        findings.append(Finding("same-origin", WARN, w))

    if not stamp:
        return findings, False

    # Stamp the run's OUTCOME (PASS|FAIL), not just a timestamp. A failing capability must be
    # distinguishable from a passing one: a bare `executed: "<ts> verify.py"` read as a clean
    # marker and masked real schema FAILs
    # (see examples/case-studies/CASE-05). WARNs do not fail — mirror main()'s exit logic (only FAIL flips outcome).
    stamped = False
    outcome = FAIL if any(f.status == FAIL for f in findings) else PASS
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_text = stamp_executed(text, ts, outcome)
    if new_text is not None:
        path.write_text(new_text)
        stamped = True
        findings.append(Finding("executed-stamp", PASS, f"stamped {ts} — outcome {outcome}"))
    else:
        findings.append(Finding("executed-stamp", WARN, "no `executed:` line in frontmatter to stamp"))
    return findings, stamped


def main(argv):
    stamp = "--no-stamp" not in argv
    argv = [a for a in argv if a != "--no-stamp"]
    if "--map" in argv:
        return run_map(REPO_ROOT)
    if "--plans" in argv:
        return run_plans(REPO_ROOT)
    if not CAPABILITIES_DIR.is_dir():
        print("review/capabilities/ does not exist yet — nothing to verify.")
        print("(The capability files may still be being authored. Exit 0: not a failure.)")
        return 0

    if argv:
        files = []
        missing = []
        for slug in argv:
            p = CAPABILITIES_DIR / f"{slug}.md"
            (files if p.exists() else missing).append(p if p.exists() else slug)
        if missing:
            print(f"unknown capability slug(s): {', '.join(str(m) for m in missing)}")
            print(f"looked in {CAPABILITIES_DIR}")
            return 1
    else:
        files = sorted(
            p for p in CAPABILITIES_DIR.glob("*.md") if p.name.lower() != "readme.md"
        )
        if not files:
            print("review/capabilities/ has no capability files yet — nothing to verify. Exit 0.")
            return 0

    any_fail = False
    summary = []
    for path in files:
        slug = path.stem
        print(f"== {slug} ==")
        findings, _ = verify_capability(path, repo_root=REPO_ROOT, stamp=stamp)
        worst = PASS
        for f in findings:
            print(f"  [{f.status}] {f.check}: {f.reason}")
            if f.status == FAIL:
                worst = FAIL
            elif f.status == WARN and worst != FAIL:
                worst = WARN
        any_fail |= worst == FAIL
        summary.append((slug, worst))
        print()

    print("== hazards (repo-wide) ==")
    for f in run_hazard_scans(REPO_ROOT):
        print(f"  [{f.status}] {f.reason}")
        # Hazard hits are WARNs by convention; they never flip the exit code.
    print()

    print("== summary ==")
    width = max((len(s) for s, _ in summary), default=0)
    for slug, worst in summary:
        print(f"  {slug.ljust(width)}  {worst}")
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
