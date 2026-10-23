# Laptop testing runbook

Document ID: `MCIAS-LAP-003` · Version: 1.0 · Date: 2026-10-11 · Status: instructions for authorized execution; not executed on the laptop

[العربية](LAPTOP_RUNBOOK.md) · [Plan](LAPTOP_TEST_PLAN_EN.md) · [Checklist](LAPTOP_TEST_CHECKLIST_EN.md) · [Report](LAPTOP_TEST_REPORT_EN.md) · [Detailed setup](WINDOWS_LAPTOP_GUIDE_EN.md)

## 1. Authorization and version pinning — LAP-01, LAP-02

Record user authorization for execution/setup/input/restart in the report before work. Document preparation is not that authorization. Read the plan/scope and designate operator/reviewer. Do not push or merge during the round; pushing this branch automatically triggers CI.

After approval, open PowerShell in a local NTFS path outside synchronization. Inspect an existing checkout rather than cloning over it, replacing it or pulling updates during the round. For a new checkout:

```powershell
git clone --branch feat/windows-laptop-testing https://github.com/overurdream-collab/test2.git
cd test2
git branch --show-current
git rev-parse HEAD
git status --short
git --version
docker version
docker compose version
docker info --format '{{.OSType}}'
wsl --version
```

Expected: correct branch, full recorded SHA, clean checkout, ready Docker and OSType=linux. If wsl --version is unsupported, record its version from Windows settings; do not change the system to bypass the check. Record Windows/browser versions, RAM and available disk. The guide's 4 GB/2 CPU allocation is a starting point, not an SLA or automatic machine change.

## 2. Authorized setup — LAP-03 through LAP-05

Start builds the image, creates key files/accounts/synthetic records and writes to DB; it is not read-only. Review existing installation ownership/data/keys first. Never transfer another machine's secrets.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Start
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Check
Invoke-RestMethod -Uri http://127.0.0.1:8000/health/ready -TimeoutSec 10
```

Bypass affects this process only; do not change machine-wide PowerShell policy. For a collision before first setup, use Start -Port 8010 and update URLs to the recorded port. The port persists; a new -Port does not change an existing installation.

Expected: healthy db/api; temporary setup; API published on 127.0.0.1 only and no DB port; readiness=ready and Check=TEST_CHECKS_PASS. A fresh database contains 12 base claims. Record build/start times separately because initial build includes downloads. Failed readiness/Check remains FAIL/BLOCKED pending diagnosis.

ACL checks after file creation do not print contents:

```powershell
(Get-Acl -LiteralPath .\deploy\laptop-private).AreAccessRulesProtected
(Get-Acl -LiteralPath .\deploy\laptop-private\.env).AreAccessRulesProtected
git check-ignore deploy/laptop-private/.env
docker compose --env-file deploy/laptop-private/.env -f deploy/compose.laptop.yml config --quiet
```

Expected: protected inheritance and Git exclusion. Locally verify access rules grant only the current user, SYSTEM and Administrators; do not publish machine account names. Never display .env, expanded config or full docker inspect.

## 3. Authentication and authorization — LAP-06 through LAP-09

Use a private console without transcription/screen sharing:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Credentials
```

Manually enroll each account secret in an Authenticator with six-digit/30-second TOTP, then sign in at `/login`. Never capture passwords, secrets or codes. Test admin/reviewer separately; logout must return protected UI to login. Replay must use the same code within its counter period; an expired period is inconclusive and needs an authorized rerun. Do not repeat failed attempts beyond the scenario; stop and record any 429.

Optional automated MFA check, only with authorization for authentication tests, not part of document preparation:

```powershell
docker compose --env-file deploy/laptop-private/.env -f deploy/compose.laptop.yml exec -T api python -m mcias.seed.laptop check --verify-mfa
```

Tests both accounts, missing/replayed codes and permission separation; writes sessions/authentication events. Do not repeat within the same TOTP period or concurrently sign in manually with these accounts.

For LAP-09, use a job_id from the authorized synthetic upload in the next section, then return here. This probe signs in as admin, requests raw records without field grants, expects 403, logs out and checks revoked-session denial with 401. It is an authorized local negative test and adds no grant. Never save token/body or enable transcription. A missing valid job means BLOCKED; hidden navigation is not server-denial evidence.

```powershell
$baseUrl = 'http://127.0.0.1:8000' # Change port only if authorized and recorded
$jobText = Read-Host 'Synthetic job_id'
$jobGuid = [Guid]::Empty
if (-not [Guid]::TryParse($jobText, [ref]$jobGuid)) { throw 'Invalid job ID' }
$protectedPassword = Read-Host 'SYN-laptop-admin password' -AsSecureString
$protectedCode = Read-Host 'Fresh TOTP code' -AsSecureString
$password = [Net.NetworkCredential]::new('', $protectedPassword).Password
$code = [Net.NetworkCredential]::new('', $protectedCode).Password
$token = $null
try {
    $payload = @{username='SYN-laptop-admin'; password=$password; totp_code=$code} | ConvertTo-Json -Compress
    $login = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/login" -ContentType 'application/json' -Body $payload
    $token = $login.access_token
    $headers = @{Authorization="Bearer $token"}
    $status = 200
    try {
        Invoke-RestMethod -Uri "$baseUrl/api/v1/ingestion/jobs/$jobGuid/records" -Headers $headers | Out-Null
    } catch {
        if ($null -eq $_.Exception.Response) { throw 'Local service unavailable' }
        $status = [int]$_.Exception.Response.StatusCode
    }
    Write-Host "Protected source probe HTTP: $status"
    if ($status -ne 403) { throw 'Expected server field-access denial' }
    Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/logout" -Headers $headers | Out-Null
    $revoked = 200
    try { Invoke-RestMethod -Uri "$baseUrl/api/v1/workspace/context" -Headers $headers | Out-Null }
    catch {
        if ($null -eq $_.Exception.Response) { throw 'Local service unavailable' }
        $revoked = [int]$_.Exception.Response.StatusCode
    }
    Write-Host "Revoked session HTTP: $revoked"
    if ($revoked -ne 401) { throw 'Expected revoked-session denial' }
} finally {
    if ($token) {
        try { Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/logout" -Headers @{Authorization="Bearer $token"} | Out-Null }
        catch { } # Session may already be revoked; do not emit exception/token
    }
    $password=$code=$payload=$token=$login=$headers=$null
    $protectedPassword.Dispose()
    $protectedCode.Dispose()
}
```

401/404/503 on the source probe are not the expected 403; record the cause without declaring PASS. Use only synthetic names/files.

## 4. Interfaces — LAP-10 through LAP-12

Open `/admin/dashboard` and `/institution/dashboard` in an authenticated session. Try AR/EN, Light/Dark, Tab, Shift+Tab, Enter and Escape. Inspect desktop, then 768 px and 390 px browser viewports; record actual dimensions. No global horizontal overflow; a table can scroll inside its container. Capture page states with synthetic data only.

Do not use `?demo=1` as API-integration evidence. Authorized demo previews have separate results and must display the synthetic banner. Unavailable/partial states must match the coverage matrix; a disabled control does not prove an implemented capability.

## 5. Inputs and reports — LAP-13 through LAP-18

With synthetic-input approval, use `/admin/reference-data` for a draft contract, tariff, category and token enrollment; record references/dates/currency. Uploading a contract does not approve it. Do not create new source files or real identity fields without separate authorization.

The 12 base claims have a metadata-only source; `demo.json` is a UI preview. Neither provides ready-to-upload originals. The integration harness generates `synthetic-workflow.csv` and `synthetic-invalid.xlsx` at execution time; they are not ready-made files in a clone. Do not run that harness on the laptop database to obtain them; it requires separately provisioned tests/environment. Upload/quarantine cases require an available approved test file or explicit permission to generate one.

Upload the existing approved synthetic source via `/admin/ingestion`; record SHA, document_id, job_id and manifest. Repeat it for duplicate detection; use only the existing approved malformed file for quarantine. Stage/resume a valid source at `/institution/claims/batches`, repeat resume and compare counts. Return to LAP-09 with a valid job from this stage.

Authorized automated alternative for sample references, one claim and MFA:

```powershell
docker compose --env-file deploy/laptop-private/.env -f deploy/compose.laptop.yml exec -T api python -m mcias.seed.laptop check --verify-mfa --verify-inputs
```

Generates/uploads `SYN-laptop.csv` and inserts records; permission must cover these actions. Stores a private `laptop-smoke.json` receipt for persistence. Do not repeat merely to inspect health. Does not cover duplicate/quarantine or every plan case. If a malformed file/tooling is missing, mark LAP-16 BLOCKED and request appropriate authorization; do not generate it automatically.

At `/institution/reports`, inspect snapshot/currency/fingerprint/source/held status; create a new test snapshot for the added batch only if authorized. Adding a claim must not alter an old report snapshot. Authorized PDF/Excel exports contain synthetic data only; save locally within the approved evidence scope and record SHA-256 using Get-FileHash. Upload/reporting is not production G5 execution or payment approval.

## 6. Persistence and resources — LAP-19, LAP-20

Record claim/contract/report counts and references before stopping, then:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Stop
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Start
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Check
docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' mcias-laptop-api-1 mcias-laptop-db-1
docker image inspect mcias-laptop:local --format '{{.Id}}'
docker compose --env-file deploy/laptop-private/.env -f deploy/compose.laptop.yml exec -T api python --version
docker compose --env-file deploy/laptop-private/.env -f deploy/compose.laptop.yml exec -T db postgres --version
```

Compare the same references/counts after Start and sign in with fresh codes. Check automatically verifies the additional claim when an automated smoke receipt exists; manually added claims require your own comparison. Start rebuilds without updating Git, but downloads/build dependencies can change the image ID; record it before/after. Container memory excludes Windows/WSL; also record Task Manager and measurement times. Never run a 10K load on this database.

## 7. Failure handling and closure — LAP-21 through LAP-24

For BLOCKED, keep step/status/SHA/environment/sanitized evidence. Do not publish raw logs; exceptions can contain data. Stop on data loss, secret exposure or authorization bypass. Stop preserves volumes but changes service state; use it within round approval and leave other applications alone.

No down -v, .env deletion or new keys over an existing DB. Restore/reset/repairs need separate authorization and the [recovery runbook](G9_DISASTER_RECOVERY_AR.md). Record out-of-scope capabilities and complete/review the report. Merge decision stays HOLD until core cases and user approval are complete; never mark GATE_STATUS ACCEPTED from this trial.
