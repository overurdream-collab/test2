# MCIAS licensing scope

The repository contains software, policy drafts, test evidence and third-party
assets with different rights. The Apache License, Version 2.0 in [LICENSE](LICENSE)
applies **only** to first-party material in the following paths:

- `mcias/` except `mcias/web_workspace/fonts/`
- `alembic/`
- `scripts/`
- `tests/`
- `.github/workflows/`
- `deploy/`
- `.dockerignore`, `.gitignore`, `alembic.ini`, `docker-compose.yml`,
  `pyproject.toml`, `package.json`, and `README.md`

Within these paths, any independently licensed third-party material retains
its own license. No additional ownership is claimed over such material.

## Not covered by this Apache-2.0 grant

- The font binaries and license texts in `mcias/web_workspace/fonts/`. Inter
  and IBM Plex are distributed under their own SIL Open Font License 1.1 terms;
  preserve their existing notices. See
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- `docs/`, including institutional policy drafts, security reports,
  screenshots, and test evidence, unless a particular file is separately
  licensed.
- `GATE_STATUS.md`, `package-lock.json`, original claim files, patient or
  insurance data, institutional contracts, credentials, private keys, and
  organizational trademarks.

Dependencies listed by package managers are subject to their own licenses;
this project license does not replace those terms.

Apache-2.0 permits commercial use, modification and redistribution of the
**covered** material, subject to its conditions. It does not certify medical
claims decisions, authorize production deployment, or permit sharing patient
data. The project is an engineering candidate; institutional approvals remain
separate.

The maintainer expressly approved this scoped Apache-2.0 grant and its
commercial-use permissions on 2026-10-22. The accompanying review report
records remaining risk limits. This license does not assign ownership of
third-party material or extend to the excluded institutional documents.
