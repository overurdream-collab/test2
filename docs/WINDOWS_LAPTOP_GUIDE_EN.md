# MCIAS on Windows 11 with 8 GB RAM

Document ID: `MCIAS-LAP-001` · Version: 1.0 · Status: synthetic local test package, not production acceptance

[العربية](WINDOWS_LAPTOP_GUIDE.md) · [Institutional requirements](policies/CLIENT_REQUIREMENTS_EN.md) · [External test plan](EXTERNAL_TEST_PLAN_EN.md)

## Package scope

Two persistent containers: PostgreSQL 16 (384 MiB limit) and Python 3.12 API (one worker, 768 MiB limit). Temporary setup has a 768 MiB limit. No Redis, Node, browser automation or ClamAV/OCR daemon bundled. Limits exclude Windows/Docker overhead and are not workload acceptance; measure on the actual laptop.

Loopback-only HTTP development profile with synthetic data, a fresh mcias_laptop_e2e database and separate source storage. Runtime DB identity differs from migration owner. Malware scanning is explicitly disabled here. Real contracts/names/records require separately authorized provisioning, keys, field grants, TLS, local scanning and approved policies; never expose this test port to the network.

## 1. Docker Desktop prerequisites

Windows 11 virtualization/WSL2 and Docker Desktop in **Linux containers** mode, running and Ready. Install Git; host Python/Node are not needed for basic operation. Use a local NTFS path such as C:\MCIAS\test2 outside OneDrive/shared/synced folders, with space for images/data.

Close heavy applications. A starting allocation for small testing is 4 GB/2 CPUs to Docker/WSL, leaving memory for Windows, not a performance guarantee. If configuring `%UserProfile%\.wslconfig`, merge rather than overwrite existing settings:

```ini
[wsl2]
memory=4GB
processors=2
swap=2GB
```

WSL limits affect other distributions. Applying changes may require restarting WSL/Docker after saving other work. The launcher never modifies this file or machine-wide PowerShell policy.

## 2. Transfer reviewed source

```powershell
git clone --branch feat/windows-laptop-testing https://github.com/overurdream-collab/test2.git
cd test2
git rev-parse HEAD
```

This is the reviewed-package feature branch. After merging, use main pinned to an independently reviewed full SHA. Never transfer .env, deploy/laptop-private or previous machine's private keys/data. First build downloads images/dependencies using verified TLS, without insecure options.

## 3. Start

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Start
```

Bypass is process-only and does not change machine policy; inspect the trusted script first. Generates random DB passwords/source/MFA keys into deploy/laptop-private/.env with NTFS ACL for current user, SYSTEM and Administrators; rejects folder/file junctions/symlinks. Excluded from Git/build context. Never put expanded `docker compose config` output in reports; use --quiet.

Builds the image, initializes schema, loads 12 held-only synthetic claims, provisions separate admin/reviewer MFA accounts and restricted runtime grants, starts API and runs checks. Never approves financial policies or creates production G5 snapshots. Repeated Start preserves keys/passwords/data; no reset.

Open http://127.0.0.1:8000/institution/dashboard and http://127.0.0.1:8000/admin/dashboard. For a port collision choose before first start:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Start -Port 8010
```

Port persists in configuration. Later change only LAPTOP_HTTP_PORT before restart, preserving keys.

## 4. Credentials/MFA

Use a private unrecorded console:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Credentials
```

Returns SYN-laptop-admin/SYN-laptop-reviewer random passwords and each totp_secret_base32. Manually enroll in an Authenticator with six-digit, 30-second TOTP. Enable automatic phone/Windows time. Login with password/code; used codes cannot be replayed. Never share/screenshot/publish output. Accounts receive no medical-field grants or production financial execution/approval permissions.

A limited synthetic reader is used by automated smoke checks; never use that account in real operation. Admin/reviewer private state resides in Docker state volume with mode 0600, not a shared Windows folder.

## 5. Local checks

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Check
```

Check covers restricted DB role/head, health, reader login/claim access, denied user administration and logout. Writes actual synthetic authentication audit events but never financial mutations; prints no session tokens/passwords. TEST_CHECKS_PASS is not gate acceptance.

Manually check RTL/LTR, Light/Dark, navigation/module search, synthetic claims/report, truthful unavailable states, login/logout and separate accounts. Record SHA, UTC date, Windows/Docker versions and per-case outcomes with sanitized screenshots in the [report template](EXTERNAL_TEST_REPORT_TEMPLATE_EN.md).

This does not run full pytest/Playwright on the usage database. Regression/restore require separate fresh databases and additional tools under the external plan. Never reset/restore/run destructive regressions on entered data. Do not claim Windows-specific success until actually tested on Windows.

## 6. Input trial sequence

1. Inventory institutional formats/fields/policies without loading real records yet.
2. Enter small synthetic contracts/tariffs/categories/enrollments via /admin/reference-data. Contracts start draft; approval requires authorization/evidence/review.
3. Upload synthetic Excel/CSV/PDF; verify hashes/manifests/quarantine, stage/resume batches and link attachments.
4. Check held reports and denied unauthorized actions; verified does not mean human approval/payment.
5. Map every institutional input to an API/schema/policy; complete missing capabilities before a full institutional trial.

| Input | Current limit |
|---|---|
| Contracts/tariffs | Governed temporal references; PDF upload does not automatically approve a contract |
| Beneficiaries | category/enrollment/beneficiary_token; no complete named personal registry |
| Mechanisms/exclusions | Explicit policy with fixed exclusion/tariff/cap/copay; no unrestricted rule editor |
| G5 UI execution | Unavailable; test harness cannot replace production governed API |
| Review/appeals | Separate events/evidence; configurable stages/full appeals incomplete |

Authorized original documents may contain names, but that does not create a structured beneficiary model. Agree name/identity fields, encryption/minimization/access before implementation.

## 7. Stop and persistence

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Stop
```

Stop preserves volumes/keys; Start resumes. Do not use down -v or Docker factory reset, which delete data. Never delete .env/regenerate keys over an existing database: evidence/MFA may become unreadable. This package adds no full backup automation; follow the [recovery runbook](G9_DISASTER_RECOVERY_AR.md) before transferring existing data.

## 8. Troubleshooting

Start Desktop/WSL2/Linux containers before use. For collisions change only port. Build failures need network/trusted certificates/space; never disable TLS. MFA failures need synchronized time/new code. Report failing step/status and Windows/Docker/SHA without .env/secrets/raw credential output. For memory pressure close applications, start with 12 claims and avoid simultaneous OCR/10K load/browser automation. Dense-file workload needs independent sizing/capability review.

### Python dependency download timeout

A `ReadTimeoutError` from `files.pythonhosted.org` during `pip install` means dependency downloading stopped before application startup. The build allows a 180-second read timeout per network wait, 10 connection-level retries and up to 3 complete install attempts with 10 seconds between attempts. This is not a deadline for the entire build. A BuildKit cache outside the image retains completed downloads for reuse; interrupted files are not guaranteed to resume. Certificate and TLS verification remain enabled.

Update the test branch and rerun Start from the project directory, preserving `.env`, volumes and cache:

```powershell
git pull --ff-only origin feat/windows-laptop-testing
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Start
```

If local edits prevent the Git update, preserve them instead of resetting them away. Persistent network failure still stops the build after three attempts; share the final error lines to investigate package repository connectivity. This change does not resolve missing connectivity or certificate rejection.

## 9. Automated verification limits

Local Linux Docker verification covered image build/migrations, restricted runtime DB identity, both MFA accounts, replay denial and API entry of a synthetic draft contract, tariff, category, enrollment and claim. The entered claim survived Stop/Start and repeated setup without reloading the original dataset.

The `Laptop Docker and Windows launcher` workflow validates PowerShell 5.1 syntax, random keys and NTFS ACLs on Windows, and the actual PowerShell launcher with Docker on Linux. It checks the published loopback port, runs `check --verify-mfa --verify-inputs` once and restarts. That optional check adds synthetic draft references/a claim and stores a private test receipt; normal Check also verifies persistence. Repeating MFA verification requires a new time counter.

These checks do not establish Docker Desktop operation on the physical laptop or 8 GB suitability for institutional workloads. Record actual Windows/WSL2, memory and input results in the external test report.

Local synthetic operation is not production or real-data approval. All gates stay OPEN until contract evidence and signatures are complete.
