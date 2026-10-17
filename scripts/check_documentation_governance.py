#!/usr/bin/env python3
"""MCIAS DG-001: verify every new meaningful commit includes its own audit record.

Usage: python scripts/check_documentation_governance.py --base <sha> --head <sha>
      [--legacy-cutoff <sha>]

Only git and the Python standard library are required. Fail closed on git errors.
"""
import argparse
import re
import subprocess
import sys

JOURNAL = "docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md"
STATE = "docs/MCIAS_V2_CURRENT_STATE_AR.md"
EXEMPT = frozenset((JOURNAL, STATE))
REQUIRED = ("Scope", "Why", "Files", "Tests", "Result", "Risks", "Next", "Handoff")
ENTRY = re.compile(r"^\+### HANDOFF-\d{8}-[A-Za-z0-9_.-]+\s*$", re.M)
FIELDS = {key: re.compile(r"^\+\- " + re.escape(key) + r":\s*\S", re.M)
          for key in REQUIRED}


def git(*args):
    completed = subprocess.run(("git", *args), capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError("git " + " ".join(args) + ": " + (completed.stderr.strip() or "failure"))
    return completed.stdout.strip()


def is_ancestor(ancestor, descendant):
    result = subprocess.run(("git", "merge-base", "--is-ancestor", ancestor, descendant),
                            capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError("unable to check Git history: " + result.stderr.strip())
    return result.returncode == 0


def changed_files(commit):
    # --first-parent intentionally inspects the first-parent result of a merge;
    # merge commits must document any resolved changes they introduce.
    return set(git("diff-tree", "--no-commit-id", "--name-only", "-r", "-m",
                   "--first-parent", commit).splitlines())


def validate_added_entry(diff):
    problems = []
    if not ENTRY.search(diff):
        problems.append("new ### HANDOFF-YYYYMMDD-NNN entry is missing")
    for key, pattern in FIELDS.items():
        if not pattern.search(diff):
            problems.append("- " + key + ": must be added in this commit")
    return problems


def validate(base, head, legacy_cutoff):
    git("rev-parse", "--verify", base + "^{commit}")
    git("rev-parse", "--verify", head + "^{commit}")
    # PR branches frequently diverge after main receives unrelated commits.
    # Scan branch-local history from the true merge base, not base_sha..head
    # directly. This avoids false positives or skipping detached branches.
    common_ancestor = git("merge-base", base, head)
    commits = git("rev-list", "--reverse", common_ancestor + ".." + head).splitlines()
    # A legacy cutoff may disappear after squash-merging and deleting a branch.
    # Never fail subsequent PRs just because its historical SHA was pruned.
    legacy_exists = subprocess.run(("git", "cat-file", "-e",
        legacy_cutoff + "^{commit}"), capture_output=True, check=False).returncode == 0 if legacy_cutoff else False
    legacy_applies = legacy_exists and is_ancestor(legacy_cutoff, head)
    errors = []
    checked = 0
    legacy = 0
    for commit in commits:
        if legacy_applies and is_ancestor(commit, legacy_cutoff):
            legacy += 1
            continue
        files = changed_files(commit)
        meaningful = files - EXEMPT
        if not meaningful:
            continue
        checked += 1
        missing = sorted(EXEMPT - files)
        if missing:
            errors.append(commit[:12] + ": documentation missing from SAME commit: " +
                          ", ".join(missing))
            continue
        diff = git("diff", "--unified=0", commit + "^", commit, "--", JOURNAL)
        problems = validate_added_entry(diff)
        if problems:
            errors.append(commit[:12] + ": " + "; ".join(problems))
        state = git("show", commit + ":" + STATE)
        for heading in ("## الحالة الآن", "## أين نتوقف؟", "## الخطوة التالية المحددة"):
            if heading not in state:
                errors.append(commit[:12] + ": state missing heading: " + heading)
    return checked, legacy, errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--legacy-cutoff", default="")
    a = p.parse_args()
    try:
        checked, legacy, errors = validate(a.base, a.head, a.legacy_cutoff)
    except RuntimeError as exc:
        print("DG-001 infrastructure error:", exc, file=sys.stderr)
        return 2
    print(f"DG-001 checked={checked}, historical-exempt={legacy}, errors={len(errors)}")
    for error in errors:
        print("DG-001 FAIL:", error, file=sys.stderr)
    if errors:
        print("For each new change, commit both the structured HANDOFF journal entry "
              "and CURRENT_STATE in the same Git commit.", file=sys.stderr)
        return 1
    print("DG-001 PASS: every applicable commit includes its documentation handoff.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
