"""Hook behaviour, driven the way Claude Code drives them: JSON payload on stdin, decision on stdout."""

import json
import os
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "template" / ".claude" / "hooks"


def run_hook(name, payload, project_dir, **env):
    proc = subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload) if not isinstance(payload, str) else payload,
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir), **env},
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def denied(out):
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


def repo_with_fence(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "protected_paths.txt").write_text(
        "# comment line\nsrc/ledger/   # money\nsrc/ids.py    # identity\n"
    )
    return tmp_path


def write(tmp_path, rel, agent=True):
    payload = {"tool_name": "Edit", "cwd": str(tmp_path), "tool_input": {"file_path": str(tmp_path / rel)}}
    if agent:
        payload["agent_id"] = "sub-1"
    return payload


# --- protect_paths ---------------------------------------------------------

def test_subagent_write_to_protected_dir_is_denied(tmp_path):
    repo = repo_with_fence(tmp_path)
    out = run_hook("protect_paths.py", write(repo, "src/ledger/post.py"), repo)
    assert denied(out)
    assert "src/ledger/post.py" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_subagent_write_to_protected_exact_file_is_denied(tmp_path):
    repo = repo_with_fence(tmp_path)
    assert denied(run_hook("protect_paths.py", write(repo, "src/ids.py"), repo))


def test_exact_entry_does_not_protect_a_prefix_sibling(tmp_path):
    repo = repo_with_fence(tmp_path)
    assert run_hook("protect_paths.py", write(repo, "src/ids.py.bak"), repo) is None


def test_main_session_is_never_fenced(tmp_path):
    repo = repo_with_fence(tmp_path)
    assert run_hook("protect_paths.py", write(repo, "src/ledger/post.py", agent=False), repo) is None


def test_subagent_write_elsewhere_is_allowed(tmp_path):
    repo = repo_with_fence(tmp_path)
    assert run_hook("protect_paths.py", write(repo, "src/ui/page.py"), repo) is None


def test_fence_off_switch(tmp_path):
    repo = repo_with_fence(tmp_path)
    assert run_hook("protect_paths.py", write(repo, "src/ledger/post.py"), repo, FALCON_FENCE="off") is None


def test_unparseable_payload_fails_open(tmp_path):
    repo = repo_with_fence(tmp_path)
    assert run_hook("protect_paths.py", "not json", repo) is None


def test_shipped_paths_file_protects_the_verifier(tmp_path):
    shipped = HOOKS.parent / "protected_paths.txt"
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "protected_paths.txt").write_text(shipped.read_text())
    assert denied(run_hook("protect_paths.py", write(tmp_path, "review/verify.py"), tmp_path))


# --- no_stash_while_live (pure parsing; the live-process probe is environment-dependent) -----

sys.path.insert(0, str(HOOKS))
from no_stash_while_live import _risky_verb  # noqa: E402


def test_risky_git_verbs_are_detected():
    assert _risky_verb("git stash") == "stash"
    assert _risky_verb("cd x && git checkout main") == "checkout"
    assert _risky_verb("git -C repo reset --hard") == "reset"


def test_read_only_and_quoted_mentions_are_not_risky():
    assert _risky_verb("git stash list") is None
    assert _risky_verb('git commit -m "never git stash here"') is None
    assert _risky_verb("echo git checkout") is None


# --- next_md_size ----------------------------------------------------------

def test_next_md_over_budget_warns_never_blocks(tmp_path):
    (tmp_path / "NEXT.md").write_text("x" * 60_000)
    out = run_hook("next_md_size.py", {}, tmp_path)
    assert "NEXT.md" in out["systemMessage"]


def test_next_md_under_budget_is_silent(tmp_path):
    (tmp_path / "NEXT.md").write_text("short")
    assert run_hook("next_md_size.py", {}, tmp_path) is None


# --- no_discard_uncommitted ---------------------------------------------------------------

def git_repo_with_dirty_file(tmp_path):
    def g(*a):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=tmp_path, check=True,
                       capture_output=True)
    g("init", "-q")
    (tmp_path / "clean.py").write_text("a = 1\n")
    (tmp_path / "dirty.py").write_text("b = 1\n")
    g("add", "-A")
    g("commit", "-qm", "init")
    (tmp_path / "dirty.py").write_text("b = 2  # uncommitted build\n")
    return tmp_path


def bash(cmd, cwd):
    return {"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": cmd}}


def test_checkout_of_a_file_with_uncommitted_changes_is_denied(tmp_path):
    repo = git_repo_with_dirty_file(tmp_path)
    assert denied(run_hook("no_discard_uncommitted.py", bash("git checkout -- dirty.py", repo), repo))
    assert denied(run_hook("no_discard_uncommitted.py", bash("git restore dirty.py", repo), repo))
    assert denied(run_hook("no_discard_uncommitted.py", bash("git checkout .", repo), repo))
    assert denied(run_hook("no_discard_uncommitted.py", bash("git reset --hard", repo), repo))


def test_cd_before_the_checkout_is_followed(tmp_path):
    (tmp_path / "r").mkdir()
    repo = git_repo_with_dirty_file(tmp_path / "r")
    elsewhere = tmp_path
    cmd = f"cd {repo} && uv run pytest -q; git checkout -- dirty.py 2>/dev/null"
    assert denied(run_hook("no_discard_uncommitted.py", bash(cmd, elsewhere), elsewhere))


def test_clean_file_branch_switch_and_mentions_are_allowed(tmp_path):
    repo = git_repo_with_dirty_file(tmp_path)
    assert not denied(run_hook("no_discard_uncommitted.py", bash("git checkout -- clean.py", repo), repo))
    assert not denied(run_hook("no_discard_uncommitted.py", bash("git checkout -b feature", repo), repo))
    assert not denied(run_hook("no_discard_uncommitted.py", bash('git commit -m "git checkout dirty.py"', repo), repo))
    assert not denied(run_hook("no_discard_uncommitted.py", bash("git reset --soft HEAD~0", repo), repo))


def test_untracked_only_tree_allows_reset_hard(tmp_path):
    repo = git_repo_with_dirty_file(tmp_path)
    (repo / "dirty.py").write_text("b = 1\n")  # back to committed
    (repo / "new.py").write_text("untracked\n")
    assert not denied(run_hook("no_discard_uncommitted.py", bash("git reset --hard", repo), repo))


# --- human_ratifies --------------------------------------------------------------------------

def plan_edit(tmp_path, old, new, agent=False):
    p = {"tool_name": "Edit", "cwd": str(tmp_path),
         "tool_input": {"file_path": str(tmp_path / "docs/plans/0001-x.md"), "old_string": old, "new_string": new}}
    if agent:
        p["agent_id"] = "sub-1"
    return p


def test_setting_a_plan_to_ratified_is_denied_even_in_the_main_session(tmp_path):
    out = run_hook("human_ratifies.py", plan_edit(tmp_path, "status: proposed", "status: ratified"), tmp_path)
    assert denied(out)
    assert "owner" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_writing_a_ratified_plan_file_is_denied(tmp_path):
    p = {"tool_name": "Write", "cwd": str(tmp_path),
         "tool_input": {"file_path": str(tmp_path / "docs/plans/0002-y.md"), "content": "---\nstatus: ratified\n---\n"}}
    assert denied(run_hook("human_ratifies.py", p, tmp_path))


def test_bash_that_ratifies_a_plan_is_denied(tmp_path):
    cmd = "sed -i '' 's/status: proposed/status: ratified/' docs/plans/0001-x.md"
    assert denied(run_hook("human_ratifies.py", bash(cmd, tmp_path), tmp_path))


def test_other_plan_edits_and_other_files_are_allowed(tmp_path):
    assert not denied(run_hook("human_ratifies.py", plan_edit(tmp_path, "## Steps", "## Steps\n1. a"), tmp_path))
    assert not denied(run_hook("human_ratifies.py", plan_edit(tmp_path, "status: draft", "status: proposed"), tmp_path))
    other = {"tool_name": "Edit", "cwd": str(tmp_path),
             "tool_input": {"file_path": str(tmp_path / "src/a.py"), "old_string": "x", "new_string": "status: ratified"}}
    assert not denied(run_hook("human_ratifies.py", other, tmp_path))
    assert not denied(run_hook("human_ratifies.py", bash("grep -c ratified docs/plans/*.md", tmp_path), tmp_path))


def test_edit_that_keeps_an_existing_ratified_line_is_allowed(tmp_path):
    old = "status: ratified\nsource_of_truth: spec.md"
    new = "status: ratified\nsource_of_truth: spec.md#fees"
    assert not denied(run_hook("human_ratifies.py", plan_edit(tmp_path, old, new), tmp_path))
