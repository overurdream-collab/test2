# DG-001 — G2 source-linked human contract review

Base SHA: 7826a886771fc1c72efcf0fde67f4b49d2b6a179
Functional UI SHA: 8b6630e4e6d5cfc03b24fa411e39bbdc1470bdda

Source PDFs yield page text records, not semantically structured contract fields. Previously contract UI requested only manifest; now it reads existing tenant-authenticated /jobs/{job_id}/records, shows raw source texts and locator, and provides an explicit human-confirmation path to create only a draft input-clause record from a verbatim excerpt. No AI attestation, policy activation, fee approval or automatic financial action. Sensitive-field access remains enforced by G2 server for records; reference.write is required for draft submission and the server retains its tenant guard. Do not assert production readiness: database roundtrip, quoted-source server-side enforcement, and add/edit acceptance remain to test. Strict browser gate must keep import BLOCKED until end-to-end source-linked draft creation is proven. No main merge or deployment.

DG-001 HANDOFF: scope=contracts import only; status=PARTIAL; branch=feat/mcias-input-triactions-e2e; current SHA pending; CI=await runs; evidence=G2 job records + Playwright screenshots; blockers=DB/browser end-to-end and source-verification guard; next=verify strict CI and repair first failure only.
