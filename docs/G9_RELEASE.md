# G9 — On-premises Release Engineering and Acceptance (NOT FOR PRODUCTION)

**Status: engineering work in progress; formal G9 gate OPEN.** Based on stacked G8 draft PR #9, which itself depends on G7 draft PR #7. None of the open G0–G8 institutional approvals are waived or inherited from synthetic CI.

## Scope and safety model

The G9 branch adds a bounded release-integrity receipt, read-only deployment preflight, synthetic performance probe, hardened encrypted backup input handling, a localhost-only HTTPS preview setup and security-negative tests.

**Do not deploy with real claims or beneficiary data.** The Docker Compose file and Dockerfile are an engineering harness, *not a signed production deployment*. Mutable base image tags, package version ranges, missing audited PostgreSQL runtime grants, key/authority custody, no real target-environment restore drill and no completed penetration test block release.

The G7 and G8 dashboards remain available on their normal paths:
- `/ui/reports` — G7 protected financial reports
- `/ui/intelligence` — G8 protected analysis and governed tasks

## Build and verify an integrity-only release candidate

Run from the repository root, on a controlled packaging machine. Do not put private environment files, TLS keys, financial records or patient source files in the package.

```bash
python -m pip install --upgrade pip
python -m pip wheel . -w dist/wheelhouse
git rev-parse HEAD
python scripts/g9_release.py build \
  --repo . --wheels dist/wheelhouse \
  --output dist/g9-candidate --commit <EXACT_40_DIGIT_COMMIT_SHA>
python scripts/g9_release.py verify --directory dist/g9-candidate
```

The receipt includes each approved engineering file and each supplied wheel's SHA-256 and byte count, the full git SHA, migration head, and `acceptance=OPEN_NOT_AUTHORIZED_FOR_PRODUCTION`. Its checksum verifies accidental or malicious changes **only when compared against an independently trusted copy of the receipt**; it is *not* a digital signature and does not establish artifact provenance, external security review or deployment authorization.

To install wheels into an **offline controlled environment**, use only the verified local wheelhouse and run `pip install --no-index --find-links dist/g9-candidate/wheels mcias`, after separately reviewing all third-party wheels and Python/runtime compatibility. The preview Dockerfile still uses a networked dependency install at **build time**, so its OCI image must be rebuilt using an independently approved offline wheelhouse, pinned image digests and isolated build controls before production acceptance.

## Private on-premises TLS preview

`deploy/compose.g9.yml` exposes only `127.0.0.1:8443` and runs private PostgreSQL on an internal Compose network with **no host port published**. The API is non-root, read-only filesystem, no Docker capabilities and no HTTP access log. Nginx uses organization-provided certificate files and blocks public OpenAPI/docs paths. All G8/G7 API permissions remain enforced server-side.

Operator provisions these files **outside version control**:

```text
deploy/private/runtime.env
deploy/private/postgres-owner.env
deploy/private/authorization-registry.json
deploy/private/tls.crt
deploy/private/tls.key
deploy/private/encrypted-sources/
```

The PostgreSQL owner account and application runtime account **must be different users**. The owning account must run Alembic migrations in a separately approved administrative session and provision the runtime SQL role and minimal table privileges. Do **not** run routine HTTP requests as the database owner or as `postgres`. The deploy preview does not silently create an application role, install database schema, create Super Admin credentials, or seed fake institutional permissions.

Runtime environment file values must be chosen and provisioned securely by the customer: `MCIAS_DATABASE_URL` (PostgreSQL, runtime account only); `MCIAS_ENVIRONMENT=production`; **no** `MCIAS_BOOTSTRAP_TOKEN`; `MCIAS_MFA_ENCRYPTION_KEY` (independently managed 32-byte secret); and a full `MCIAS_RELEASE_COMMIT` SHA. PostgreSQL owner environment separately supplies `POSTGRES_USER`, `POSTGRES_DB`, and `POSTGRES_PASSWORD`. The target organization must control certificates and signing keys outside source control. Docker bind-mount permissions must allow the non-root application ID 1900 to read the authorization registry (non-group-writable), and Nginx to read the certificate and key, without exposing either publicly.

All `deploy/private/**` paths are ignored by Git. These are **example paths only**, not real credentials.

A separate institutional reverse proxy, firewall and trusted private DNS are needed before any external network access. The preview's localhost-only port is intentional; *never change it to `0.0.0.0` based on this draft alone*.

## Read-only preflight

On the **target host**, with its intended runtime-only PostgreSQL user, after provisioning controlled environment values:

```bash
python -m mcias.preflight_g9 --check-database
```

The JSON response never prints passwords, full connection URIs, raw keys, patient data or institution identifiers. It checks production bootstrap disabled, PostgreSQL runtime credentials present, migration at `0016_g8_signal_review`, runtime account not superuser/owner/DDL creator, no UPDATE or DELETE permission on `audit_log`, non-writable institution authorization registry and trusted SAN certificate with more than 30 days before expiry. The certificate's hostname and local path come from `MCIAS_TLS_HOST` and `MCIAS_TLS_CERT_PATH`.

Exit code `2` means engineering checks are blocked. Even if it exits `0`, the response always shows `production_accepted: false` because a separate signed institutional gate and other controls are required.

The configuration validator cannot prove possession/rotation of MFA keys, validity of the independent head authority registry, firewall rules, TLS trust chain, encryption key escrow, a full backup restore, approved financial policy, operational log custody or a penetration test. **None of those are implicitly accepted.**

## Synthetic workload probe

```bash
python -m mcias.performance_g9 --claims 1000 --repeats 3
```

Results include actual measured median/worst timing and deterministic output hash for synthetic G8 analytics. The probe uses no database, network or patient data. It cannot establish accepted performance of real institutional input, PostgreSQL concurrency, document extraction, claim audits, Arabic PDF export or disaster recovery.

A signed organizational `N` claims, concurrency, P95 and recovery-time target must be specified before the G9 performance/restore acceptance test can be considered passed. Until then the reported value is `NO_INSTITUTION_APPROVED_SLA`.

## Existing and added quality gates

- Full predecessor G0–G8 unit and real PostgreSQL test suite **on the exact G9 commit**.
- G9 negative tests: manipulated and traversal-containing backups, spoofed/altered release manifest, mismatched/expiring TLS certificates, insecure settings and leaking secrets, symlinked release artifacts, expired/bootstrap misuse, server docs access in production.
- Real-world privacy/least-privilege acceptance must additionally include MFA provisioning, institutional role matrix, authorized source field export review, host vulnerability scanning, encryption key rotation, HTTP TLS scan, PostgreSQL readonly-role negative tests, full restore of *both* PostgreSQL and encrypted source storage, backup SHA-256 source verification and independent witness.
- Track unresolved G0–G8 approvers in `docs/G0_G8_ACCEPTANCE_TRACKER.md`. G9 inherits every prior blocker and cannot be declared green due to code tests alone.

## Known blockers and handoff

1. Independent institutional approval of pricing, contract precedence, currency, rounding and medical field permissions (**G0/G3/G5/G7**).
2. Formal stage-by-stage multi-level claims approval and re-audit signoff (**G6**).
3. Measured positive/false-positive review calibration using permitted locally controlled data (**G8**).
4. Actual least-privilege PostgreSQL service role grants and access tests, approved TLS certificate chain, protected Ed25519 authorization registry and key custody.
5. Pinned and audited offline image/third-party dependency hashes, an organization-signed release manifest, security threat/penetration review, target-hardware concurrency/load benchmarks and independent disaster recovery.
6. Human signoff **G0 through G9**, exact CI reference, installation UAT and rollback rehearsal.

All prior PRs remain drafts pending independent review. A future release PR may only target `main` after dependency PRs are reviewed in order and every mandatory gate is signed. Until then, the release candidate is an **engineering preview** only.
