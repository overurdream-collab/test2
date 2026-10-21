# MCIAS — scoped Apache-2.0 licensing review

**Date:** 2026-10-22 · **Status:** MAINTAINER APPROVED FOR LICENSE MERGE; RELEASE SECURITY REMAINS OPEN

## Scope

Prepare a restricted Apache-2.0 grant for original software and engineering
tests, leaving institutional documents and external fonts outside it. The operative scope is defined by
`LICENSE_SCOPE.md`; the canonical license text is in `LICENSE`.

## Why

The public MCIAS repository previously had no recognized software license.
Public GitHub visibility by itself is not an open-source license. The user
approved Apache-2.0 for eligible components, confirmed ownership and the
right to allow commercial reuse, and explicitly authorized merging PR #37
into `main`. This does **not** approve production use or disclosure of
institutional records.

## Evidence register

| ID | Inspection | Observation |
| --- | --- | --- |
| L-01 | `main` commit | `b69defa2f621458ef44d790b510840307a81009a`; unchanged during inspection |
| L-02 | Git authors, complete history reachable from `main` | 524 commits attributed to `overurdream-collab <over.ur.dream@gmail.com>` and 14 to `Ahmed Kuhlani <numbersinchina@gmail.com>`. Attribution alone does not prove copyright ownership or absence of imported code. |
| L-03 | Tracked file inventory | About 348 tracked paths; no tracked `.xlsx`, `.csv`, `.pdf`, `.db`, `.sqlite`, `.pem`, `.p12`, `.pfx`, or `.key` matches by suffix. Filename checking cannot prove content safety. |
| L-04 | Seed fixture and policy review | The committed workspace seed is marked synthetic; policy docs forbid placing beneficiary identities and source clinical records in Git. This is not a full privacy audit. |
| L-05 | Bundled license inventory | Inter and IBM Plex each retain their separately supplied SIL OFL-1.1 license notice. |
| L-06 | Pattern scan | No matches for common private-key headers, long `sk-` tokens, AWS access-key IDs, or GitHub token prefixes in tracked source by the limited scan. Three scripts/tests contain password variables in synthetic testing contexts; these are not treated as proof of leaked production credentials. |
| L-07 | Dependency manifests | Python dependencies are declared in `pyproject.toml`; the JavaScript test dependency is in `package.json`. Dependencies are not relicensed. |
| L-08 | History-wide secret scan | Official Gitleaks v8.30.1 release, SHA256 `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`; 532 commits scanned. All 23 findings were the `generic-api-key` rule on `docs/evidence/**/source-integrity.json` SHA256 digest mappings, not evidenced API credentials. The working-tree scan returned the same 23 findings. No scanner can prove the absence of every secret. |
| L-09 | JavaScript dependency-license inventory | `package-lock.json` contains one package entry, `axe-core` v4.10.3, marked MPL-2.0. This dependency is independently licensed and excluded from the first-party grant. Python direct dependencies are listed in `pyproject.toml`; installed/transitive licenses require separate verification before redistribution. |
| L-10 | Current CI | Unit and PostgreSQL Integration passed on PR #37. Dependency Audit failed on the pre-existing `Pillow>=11,<13` constraint (Pillow 12.3.0 has 24 advisories); license changes have no runtime dependencies. The maintainer expressly acknowledged this baseline issue when authorizing the license-only merge. |

## Open decisions / risks

1. **Owner confirmed:** the maintainer has the right to license the covered
   original code, including authorized contributions, and accepts the
   commercial reuse allowed by Apache-2.0. This is a maintainer attestation,
   not an independent copyright opinion.
2. Third-party source provenance still warrants ongoing review; Git authorship
   and pattern searches cannot independently rule out every imported snippet.
3. Secret scanning of the whole reachable Git history and worktree completed;
   23 flagged file-digest values were classified as non-secret SHA256 hashes.
   Subsequent changes must still be scanned.
4. Dependencies are separately licensed. The JavaScript lock's license was
   inventoried; Python transitive-license due diligence and the identified
   Pillow vulnerability remediation remain OPEN for any release.
5. The grant expressly excludes policy drafts, reports, screenshots, patient
   data and trademarks. Do not describe the **entire** repository as Apache-2.0.

## Tests / verification

- [x] Retrieved a clean `main` snapshot and complete reachable history.
- [x] Reviewed the README, manifest files, synthetic seed, policies, bundled
      font notices, tracked paths and limited credential patterns.
- [x] `cmp -s LICENSE /usr/share/common-licenses/Apache-2.0` passed,
      establishing an exact match to the installed canonical license text.
- [x] `git diff --check` passed for the proposed changes.
- [x] PR #37 Unit and PostgreSQL jobs passed; Dependency Audit failure recorded.
- [x] Owner confirmed rights, commercial permissions, scope and license-only merge.
- [x] Whole-history and worktree Gitleaks scan; findings triaged to SHA256 maps.
- [ ] Full release/deployment security clearance and transitive dependency audit.

## Handoff

The maintainer expressly authorized a license-only merge of PR #37, aware
of the existing Pillow dependency-audit failure. This permission is limited
to the enumerated first-party licensing files and does not authorize a
runtime release, deploy, other PR merges, or a security-gate bypass.
No runtime code, patient records, CI tests, or security gates were altered
for grant eligibility. Before the merge is confirmed, the OpenAI application
must accurately describe the **default branch** as previously unlicensed;
after confirmation, it may accurately describe the scoped Apache-2.0 grant.
