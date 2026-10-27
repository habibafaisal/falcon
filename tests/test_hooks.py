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
