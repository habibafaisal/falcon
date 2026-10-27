"""Tests for verify.py --plans: no UNDERSTAND-IT (protected-path) change without a ratified plan."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "template" / "review"))

from verify import FAIL, PASS, check_plans, load_plans, load_protected_entries  # noqa: E402

PROTECTED = ("src/ledger/", "src/auth/permissions.py")


def plan(status="ratified", paths=("src/ledger/",), name="p"):
    return {"plan": name, "status": status, "protected_paths": list(paths), "_file": f"docs/plans/{name}.md"}


def statuses(findings):
    return [f.status for f in findings]


def test_unprotected_change_needs_no_plan():
    findings = check_plans(["src/ui/button.py"], PROTECTED, [])
    assert FAIL not in statuses(findings)


def test_protected_change_without_plan_fails():
    findings = check_plans(["src/ledger/post.py"], PROTECTED, [])
    assert statuses(findings) == [FAIL]
    assert "src/ledger/post.py" in findings[0].reason


def test_ratified_plan_covering_directory_passes():
    findings = check_plans(["src/ledger/post.py"], PROTECTED, [plan()])
    assert statuses(findings) == [PASS]


def test_proposed_plan_does_not_count():
    findings = check_plans(["src/ledger/post.py"], PROTECTED, [plan(status="proposed")])
    assert statuses(findings) == [FAIL]
    assert "not ratified" in findings[0].reason


def test_plan_for_other_path_does_not_cover():
    findings = check_plans(["src/auth/permissions.py"], PROTECTED, [plan(paths=("src/ledger/",))])
    assert statuses(findings) == [FAIL]


def test_exact_file_entry_matches_only_that_file():
    findings = check_plans(["src/auth/permissions_test_helpers.py"], PROTECTED, [])
    assert FAIL not in statuses(findings)


def test_plan_naming_a_file_inside_protected_dir_covers_it():
    findings = check_plans(["src/ledger/post.py"], PROTECTED, [plan(paths=("src/ledger/post.py",))])
    assert statuses(findings) == [PASS]


def test_load_plans_reads_frontmatter_and_skips_template(tmp_path):
    d = tmp_path / "docs" / "plans"
    d.mkdir(parents=True)
    (d / "0000-template.md").write_text("---\nplan: template\nstatus: ratified\nprotected_paths: [src/]\n---\n")
    (d / "0001-fee.md").write_text("---\nplan: fee\nstatus: ratified\nprotected_paths:\n  - src/ledger/\n---\nbody\n")
    (d / "0002-bad.md").write_text("no frontmatter here\n")
    plans, errors = load_plans(d)
    assert [p["plan"] for p in plans] == ["fee"]
    assert len(errors) == 1 and "0002-bad.md" in errors[0]


def test_load_protected_entries_strips_comments(tmp_path):
    f = tmp_path / "protected_paths.txt"
    f.write_text("# header\nsrc/ledger/   # balance\n\nreview/verify.py # boundary\n")
    assert load_protected_entries(f) == ("src/ledger/", "review/verify.py")
