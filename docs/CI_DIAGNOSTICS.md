# CI Diagnostics — 2026-10-10

Repository visibility verified: public.
Commit inspected: a2a00188efbd7e590acae646defbb422aba1d473.
GitHub Actions run #11: 37999229425, workflow "MCIAS G1 checks", completed with failure.
- Job 114052947489: unit — failure.
- Job 114052947345: dependency-audit — failure.
- GitHub job steps endpoint returned empty arrays for both jobs.
- Job log retrieval returned BlobNotFound (404) for both jobs.

## Interpretation
CI is triggering, but **the underlying failure cause cannot be established from the currently accessible logs**. Empty steps could indicate a runner provisioning or pre-execution failure, but this is a hypothesis, not a diagnosis. Do not claim Python test failures or vulnerability findings without logs.

## Required follow-up
1. Inspect the run directly in GitHub Actions UI: https://github.com/overurdream-collab/test2/actions/runs/37999229425
2. Check repository Actions settings, runner provisioning, billing/usage and workflow permissions.
3. Re-run the workflow once logs are available; collect failing command and full stderr.
4. Fix any confirmed source/dependency issue, then run both jobs on the same commit.
5. Record run ID, commit SHA, result and log evidence in GATE_STATUS.md.
6. Do not accept G1 until all required tests, real PostgreSQL recovery and human sign-off succeed.


## Resolution — verified GitHub run #15
Re-run of #11: unit SUCCESS; dependency-audit FAILURE. Full audit log showed 7 advisory entries for cryptography 46.0.7 (PYSEC-2026-3552/3553/3554, GHSA-537c-gmf6-5ccf). Upgraded dependency bound from cryptography>=43,<47 to cryptography>=50.0.0,<51, commit a33a7257f244f65c3c586095f99afc28d374deed.

GitHub Actions run #15: https://github.com/overurdream-collab/test2/actions/runs/38000684160
- unit: completed SUCCESS (job 114057725578).
- dependency-audit: completed SUCCESS (job 114057725305).
This closes the observed dependency-audit CI failure, **not** G1 acceptance or a general security certification.
