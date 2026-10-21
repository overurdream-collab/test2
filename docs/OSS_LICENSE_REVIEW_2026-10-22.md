# MCIAS — scoped Apache-2.0 licensing review

**Date:** 2026-10-22 · **Status:** DRAFT / NOT APPROVED FOR MERGE

## Scope

Prepare a restricted Apache-2.0 grant for original software and engineering
tests, leave institutional documents and external fonts outside it, and open a
draft review without changing `main`. The operative scope is defined by
`LICENSE_SCOPE.md`; the canonical license text is in `LICENSE`.

## Why

The public MCIAS repository previously had no recognized software license.
Public GitHub visibility by itself is not an open-source license. The user
approved Apache-2.0 for eligible components following a rights/security
review, but did **not** approve a merge, production use, or disclosure of
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

## Open decisions / risks

1. Confirm the user or their legal entity holds the right to license the
   first-party code, including any AI-assisted and contractor contributions.
2. Review code and assets against any upstream third-party source copied into
   the project; Git author metadata cannot establish independent authorship.
3. Run a full secret scanner and dependency-license inventory before merge;
   limited local regex/extension checks are **not** a security certification.
4. Verify that the scoped grant is commercially intended. Apache-2.0
   allows downstream commercial exploitation of covered source code.
5. Confirm exclusion of policy drafts, reports, screenshots, patient data and
   trademarks is acceptable; do not claim the entire repository is under
   Apache-2.0.

## Tests / verification

- [x] Retrieved a clean `main` snapshot and complete reachable history.
- [x] Reviewed the README, manifest files, synthetic seed, policies, bundled
      font notices, tracked paths and limited credential patterns.
- [x] `cmp -s LICENSE /usr/share/common-licenses/Apache-2.0` passed,
      establishing an exact match to the installed canonical license text.
- [x] `git diff --check` passed for the proposed changes.
- [ ] PR CI on the new HEAD, if triggered.
- [ ] Final human copyright / security approval.

## Handoff

The licensing branch and Draft PR are a review vehicle only. Do not merge
without explicit owner approval and resolution of the open decisions. No
runtime code, patient records, CI tests, or security gates are to be altered
for the sake of grant eligibility. The OpenAI grant application must describe
the licensing status of the **default branch** honestly until a verified
license is actually merged.
