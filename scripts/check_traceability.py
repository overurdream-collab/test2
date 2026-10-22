"""Per-commit MCIAS traceability guard, standard-library-only and fail-closed."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOG_PREFIX = "docs/engineering/worklogs/"
FIELDS = ("event_id:", "when_utc:", "actor:", "action:", "reason:", "scope:",
          "before_sha:", "after_ref:", "files_or_sources:", "command_or_method:",
          "expected:", "outcome:", "validation:", "evidence:", "risk_and_security:",
          "rollback:", "next:", "decision_status:")


def git(root, *args):
    done = subprocess.run(["git", *args], cwd=root, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if done.returncode:
        raise RuntimeError("git " + " ".join(args) + ": " + done.stderr.strip())
    return done.stdout.strip()


def verify(root, cutoff):
    if not re.fullmatch(r"[0-9a-f]{40}", cutoff):
        return ["Invalid full SHA in traceability baseline"]
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", cutoff, "HEAD"],
                              cwd=root, capture_output=True)
    if ancestor.returncode:
        return ["Traceability baseline is not reachable from HEAD"]
    commits = git(root, "rev-list", "--reverse", cutoff + "..HEAD").splitlines()
    errors = []
    checked = 0
    for sha in commits:
        relation = git(root, "rev-list", "--parents", "-n", "1", sha).split()
        if len(relation) != 2:
            continue  # The constituent PR commits are checked separately.
        parent = relation[1]
        paths = git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", sha).splitlines()
        if not paths or all(path.startswith(LOG_PREFIX) for path in paths):
            continue  # Logs cannot recursively demand a log for a log.
        checked += 1
        logs = [p for p in paths if p.startswith(LOG_PREFIX) and p.endswith(".md")
                and not p.endswith("/_TEMPLATE.md")]
        if not logs:
            errors.append(sha[:12] + ": file change without same-commit worklog")
            continue
        patch = git(root, "show", "--format=", "--unified=0", sha, "--", *logs)
        additions = "\n".join(row[1:] for row in patch.splitlines()
                              if row.startswith("+") and not row.startswith("+++"))
        absent = [key for key in FIELDS if key not in additions]
        if absent:
            errors.append(sha[:12] + ": incomplete added event fields " + ", ".join(absent))
        if "before_sha: " + parent not in additions:
            errors.append(sha[:12] + ": recorded before_sha is not the real parent")
        if "after_ref: SELF" not in additions:
            errors.append(sha[:12] + ": after_ref SELF missing")
    print("Traceability checked: commits=%s, tracked_changes=%s, violations=%s"
          % (len(commits), checked, len(errors)))
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff", default=None)
    args = parser.parse_args()
    try:
        cutoff = args.cutoff or (ROOT/"docs/engineering/TRACEABILITY_BASE_SHA").read_text().strip()
        problems = verify(ROOT, cutoff)
    except (RuntimeError, OSError) as exc:
        problems = [str(exc)]
    for problem in problems:
        print("TRACEABILITY FAILURE: " + problem, file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
