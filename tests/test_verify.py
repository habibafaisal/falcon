"""Tests for the pure parts of review/verify.py (the review-harness deterministic layer).

Subprocess-facing checks (pytest runs, git log) are factored behind small
functions in verify.py; here we test only the parsing/logic — no pytest-in-pytest,
no real git.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "template" / "review"))

from verify import (  # noqa: E402
    check_evidence_paths,
    check_same_origin,
    check_schema,
    is_cross_repo_evidence,
    parse_frontmatter,
    parse_hazard_rows,
    parse_pytest_summary,
    stamp_executed,
    verify_capability,
)

VALID_FM = """\
---
capability: seal-write-path
capability_state: validated
permitted_use: historical_backtest
authority:
  - source: spec/interfaces.md
    pointer: "append-only section"
governing_tests:
  - tests/test_canonical.py
scenarios:
  S1:
    status: demonstrated
    evidence: tests/test_canonical.py
    concern: null
evidence_class: 2
executed: null
---

# Seal write path

Prose verdict here.
"""


# --- frontmatter parse + schema -------------------------------------------

def test_valid_frontmatter_parses_and_passes_schema():
    fm, err = parse_frontmatter(VALID_FM)
    assert err is None
    assert fm["capability"] == "seal-write-path"
    assert check_schema(fm) == []


def test_missing_fences_is_a_parse_error_not_a_crash():
    fm, err = parse_frontmatter("# just prose, no frontmatter\n")
    assert fm is None
    assert "fences" in err


def test_bad_vocab_is_rejected():
    fm, _ = parse_frontmatter(VALID_FM.replace("validated", "done").replace(
        "historical_backtest", "yolo_live"))
    errors = check_schema(fm)
    assert any("capability_state" in e for e in errors)
    assert any("permitted_use" in e for e in errors)


def test_missing_required_key_is_reported_by_name():
    fm, _ = parse_frontmatter(VALID_FM)
    del fm["governing_tests"]
    errors = check_schema(fm)
    assert any("governing_tests" in e for e in errors)


def test_bad_scenario_status_and_key_shape_are_rejected():
    fm, _ = parse_frontmatter(VALID_FM)
    fm["scenarios"] = {"S1": {"status": "vibes"}, "X9": {"status": "demonstrated"}}
    errors = check_schema(fm)
    assert any("'vibes'" in e for e in errors)
    assert any("X9" in e for e in errors)


def test_evidence_class_must_be_int_0_to_5():
    fm, _ = parse_frontmatter(VALID_FM)
    fm["evidence_class"] = 7
    assert any("evidence_class" in e for e in check_schema(fm))


# --- review_log (reuse-probe, docs/reuse_experiment.md) ---------------------

def test_review_log_is_optional_and_absent_by_default():
    fm, _ = parse_frontmatter(VALID_FM)
    assert "review_log" not in fm
    assert check_schema(fm) == []


def test_valid_review_log_entry_passes():
    fm, _ = parse_frontmatter(VALID_FM)
    fm["review_log"] = [{
        "scenario": "S1",
        "reviewed_commit": "abc1234",
        "reviewed_at": "2026-09-19T00:00:00Z",
        "verdict": "demonstrated",
    }]
    assert check_schema(fm) == []


def test_review_log_entry_missing_a_field_is_reported():
    fm, _ = parse_frontmatter(VALID_FM)
    fm["review_log"] = [{"scenario": "S1", "verdict": "demonstrated"}]
    errors = check_schema(fm)
    assert any("reviewed_commit" in e for e in errors)
    assert any("reviewed_at" in e for e in errors)


def test_review_log_entry_referencing_unknown_scenario_is_rejected():
    fm, _ = parse_frontmatter(VALID_FM)
    fm["review_log"] = [{
        "scenario": "S99",
        "reviewed_commit": "abc1234",
        "reviewed_at": "2026-09-19T00:00:00Z",
        "verdict": "demonstrated",
    }]
    errors = check_schema(fm)
    assert any("S99" in e and "not a key in scenarios" in e for e in errors)


def test_review_log_entry_bad_verdict_is_rejected():
    fm, _ = parse_frontmatter(VALID_FM)
    fm["review_log"] = [{
        "scenario": "S1",
        "reviewed_commit": "abc1234",
        "reviewed_at": "2026-09-19T00:00:00Z",
        "verdict": "vibes",
    }]
    errors = check_schema(fm)
    assert any("'vibes'" in e for e in errors)


# --- evidence path check ---------------------------------------------------

def test_evidence_paths_in_repo_pass(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("")
    errors, warnings = check_evidence_paths(["tests/test_x.py"], tmp_path)
    assert errors == [] and warnings == []


def test_tmp_and_absolute_paths_are_rejected_even_if_they_exist(tmp_path):
    real = tmp_path / "evidence.txt"
    real.write_text("exists on this machine only")
    errors, _ = check_evidence_paths([str(real), "/tmp/out.log"], tmp_path)
    assert len(errors) == 2
    assert all("absolute path" in e for e in errors)


def test_missing_relative_path_is_reported(tmp_path):
    errors, _ = check_evidence_paths(["tests/nope.py"], tmp_path)
    assert errors == ["tests/nope.py: does not exist in repo"]


def test_line_anchor_suffix_is_stripped_before_existence_check(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "audit.py").write_text("")
    errors, warnings = check_evidence_paths(["app/audit.py#L42", "app/audit.py:17"], tmp_path)
    assert errors == [] and warnings == []


# --- cross-repo evidence prefix (ratified gate-hygiene, 2026-08-17) ---------

def test_cross_repo_prefix_is_warn_not_fail(tmp_path):
    # `FE:src/foo.tsx` lives in another repo — existence-exempt, must WARN not FAIL.
    errors, warnings = check_evidence_paths(["FE:src/components/foo.tsx"], tmp_path)
    assert errors == []
    assert len(warnings) == 1 and "cross-repo" in warnings[0]


def test_in_repo_missing_path_still_fails_alongside_cross_repo(tmp_path):
    errors, warnings = check_evidence_paths(
        ["FE:src/components/foo.tsx", "tests/nope.py"], tmp_path
    )
    assert errors == ["tests/nope.py: does not exist in repo"]
    assert len(warnings) == 1


def test_line_anchor_is_not_mistaken_for_cross_repo(tmp_path):
    # `app/foo.py:42` has DIGITS after the `:` — a line anchor, not a repo prefix.
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "foo.py").write_text("")
    assert not is_cross_repo_evidence("app/foo.py:42")
    assert is_cross_repo_evidence("FE:src/foo.tsx")
    errors, warnings = check_evidence_paths(["app/foo.py:42"], tmp_path)
    assert errors == [] and warnings == []


# --- pytest summary parsing ------------------------------------------------

def test_summary_all_passed():
    out = "....\n4 passed in 0.12s\n"
    assert parse_pytest_summary(out) == {"passed": 4, "skipped": 0, "failed": 0, "errors": 0}


def test_summary_with_skips_split_out():
    out = "..s.s\n3 passed, 2 skipped in 0.3s\n"
    counts = parse_pytest_summary(out)
    assert counts["passed"] == 3
    assert counts["skipped"] == 2
    assert counts["failed"] == 0


def test_summary_with_failures_and_errors():
    out = "1 failed, 2 passed, 1 error in 0.5s\n"
    counts = parse_pytest_summary(out)
    assert counts == {"passed": 2, "skipped": 0, "failed": 1, "errors": 1}


def test_summary_with_warnings_noise_does_not_pollute_counts():
    out = "5 passed, 3 warnings in 1.02s\n"
    counts = parse_pytest_summary(out)
    assert counts == {"passed": 5, "skipped": 0, "failed": 0, "errors": 0}


def test_no_summary_line_returns_none():
    assert parse_pytest_summary("ERROR: file or directory not found: tests/x.py\n") is None


# --- executed stamp --------------------------------------------------------

def test_stamp_rewrites_only_the_executed_line():
    stamped = stamp_executed(VALID_FM, "2026-07-26T12:00:00Z", "PASS")
    assert stamped is not None
    assert 'executed: "2026-07-26T12:00:00Z verify.py PASS"' in stamped
    # Every other byte is preserved: removing the two executed lines from each
    # version leaves identical text.
    strip = lambda t: "\n".join(  # noqa: E731
        line for line in t.split("\n") if not line.startswith("executed:"))
    assert strip(stamped) == strip(VALID_FM)


def test_stamp_encodes_the_run_outcome_so_a_fail_is_not_green():
    """A failing capability must NOT read as green. The stamp carries PASS|FAIL, never a
    bare timestamp that NEXT.md/readers treat as clean (CASE-05)."""
    passed = stamp_executed(VALID_FM, "2026-07-26T12:00:00Z", "PASS")
    failed = stamp_executed(VALID_FM, "2026-07-26T12:00:00Z", "FAIL")
    assert 'executed: "2026-07-26T12:00:00Z verify.py PASS"' in passed
    assert 'executed: "2026-07-26T12:00:00Z verify.py FAIL"' in failed
    assert passed != failed  # the outcome is visible in the stamped bytes


def test_no_stamp_run_leaves_the_capability_file_byte_identical(tmp_path):
    """The pre-commit gate must only READ. A stamping run rewrites `executed:` in the very file
    being committed, so the tree is dirty again right after every commit — the leftover change
    that invites a `git stash` over a parallel session's work (M10, M23)."""
    cap = tmp_path / "seal-write-path.md"
    cap.write_text(VALID_FM)
    findings, stamped = verify_capability(cap, repo_root=tmp_path, stamp=False)
    assert stamped is False
    assert cap.read_text() == VALID_FM
    assert all(f.check != "executed-stamp" for f in findings)


def test_default_run_still_stamps(tmp_path):
    cap = tmp_path / "seal-write-path.md"
    cap.write_text(VALID_FM)
    _, stamped = verify_capability(cap, repo_root=tmp_path)
    assert stamped is True
    assert "verify.py" in cap.read_text()


def test_stamp_returns_none_when_no_executed_line():
    text = VALID_FM.replace("executed: null\n", "")
    assert stamp_executed(text, "2026-07-26T12:00:00Z", "PASS") is None


def test_stamp_does_not_touch_executed_looking_text_in_prose():
    text = VALID_FM + "\nexecuted: this prose line must survive\n"
    stamped = stamp_executed(text, "2026-07-26T12:00:00Z", "PASS")
    assert stamped.endswith("\nexecuted: this prose line must survive\n")


# --- hazard row parsing ----------------------------------------------------

HAZARDS_MD = """\
# Hazards

| id | detection | blocks |
|---|---|---|
| H1 | `grep -rn "float(" app/rules/` | Decimal only |
| H2 | manual review | n/a |
| H3 | when `KNOWN_ISSUES.md` flips to BUILT, reconcile every cross-ref | review-read |
| H4 | `uv lock --check` (drift ⇒ replay breaks) | pin deps |
"""


def test_hazard_rows_are_runnable_only_when_the_cell_leads_with_the_command():
    rows, skipped = parse_hazard_rows(HAZARDS_MD)
    # H1/H4 lead with a backticked command (optionally annotated) → runnable.
    assert ("H1", 'grep -rn "float(" app/rules/') in rows
    assert ("H4", "uv lock --check") in rows
    # H2 (no backtick) and H3 (backtick buried mid-prose = a filename being discussed,
    # NOT a command) are review-reads, never run.
    assert set(skipped) == {"H2", "H3"}


def test_prose_row_with_embedded_backtick_is_a_review_read_not_a_command():
    """The false-clean bug (CASE-05): a backtick buried in a prose sentence
    (HZ-11 `KNOWN_ISSUES.md`, HZ-12 `cp`) was extracted and run as a shell command;
    it errored to empty stdout and the gatekeeper printed [PASS] clean. Such a row must
    be SKIPPED as a review-read, and its embedded token must never become a command."""
    rows, skipped = parse_hazard_rows(HAZARDS_MD)
    assert "H3" in skipped
    assert all(cmd != "KNOWN_ISSUES.md" for _, cmd in rows)
    assert "H3" not in [hid for hid, _ in rows]


def test_hazard_header_and_separator_rows_are_ignored():
    rows, skipped = parse_hazard_rows(HAZARDS_MD)
    ids = [r[0] for r in rows] + skipped
    assert "id" not in ids
    assert not any(set(i) <= {"-", ":"} for i in ids)


# --- same-origin flag (injected git lookup, no real git) -------------------

def test_same_origin_flags_shared_introducing_commit():
    fm = {
        "authority": [{"source": "app/audit.py", "pointer": "p"}],
        "governing_tests": ["tests/test_audit.py"],
    }
    intros = {"app/audit.py": "abc123def456", "tests/test_audit.py": "abc123def456"}
    warnings = check_same_origin(fm, "/repo", get_intro=lambda p, _: intros[p])
    assert len(warnings) == 1
    assert "same-origin evidence" in warnings[0]


def test_different_origins_produce_no_warning():
    fm = {
        "authority": [{"source": "app/audit.py", "pointer": "p"}],
        "governing_tests": ["tests/test_audit.py"],
    }
    intros = {"app/audit.py": "aaa", "tests/test_audit.py": "bbb"}
    assert check_same_origin(fm, "/repo", get_intro=lambda p, _: intros[p]) == []


def test_non_app_authority_sources_are_not_origin_checked():
    fm = {
        "authority": [{"source": "spec/guide.md", "pointer": "p"}],
        "governing_tests": ["tests/test_audit.py"],
    }
    called = []
    check_same_origin(fm, "/repo", get_intro=lambda p, _: called.append(p) or "x")
    assert called == []
