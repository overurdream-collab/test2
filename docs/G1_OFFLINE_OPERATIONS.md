# G1 offline key and recovery operations

All recovery operations are offline, require a controlled workstation and audited access, and must not be exposed through a public API.

## Recovery
- Provision two independent trusted Ed25519 public keys after verifying approver identities and authority out of band. Never accept keys submitted with the request.
- Obtain a written recovery request, identity evidence and its SHA-256 digest, an expiration time, and a unique request ID.
- Have each approver sign the identical canonical JSON request independently.
- Run the offline recovery procedure in an exclusive maintenance window. It replaces the MFA secret, keeps MFA enabled, revokes sessions and records approvers.
- Transfer the newly issued TOTP secret over an approved out-of-band channel. Require the subject to prove possession before resuming production access.
- Review the audit trail and reject repeated request IDs. Database-owner tampering remains a residual threat.

## Key rotation
- Keep old and new AES-256 keys in separate controlled stores; never commit them or print them.
- Stop authentication traffic, back up the database and encrypted source files, and verify that the old key can decrypt a recovery sample.
- Rotate MFA factor envelopes transactionally; verify all envelopes with the new key and record counts.
- Change the runtime key only after successful verification; revoke sessions and restart processes.
- Restore from a tested backup with the old key if verification fails. Retain the old key until the rollback window closes.

## Written authorizations
- The organization-head identity, authority and public key must be verified independently.
- A detached Ed25519 signature must validate against the exact archived bytes and SHA-256.
- The signature verification primitive exists, but production rule activation remains disabled until an approved trusted-key registry and authorization workflow are integrated.

## Operational acceptance not simulated by CI
- Signed organization approvals and independent key custody.
- TLS deployment and certificate validation on the target server.
- Least-privilege application database account verified against deployed PostgreSQL.
- Full disaster-recovery drill on an isolated target environment.

## Production rule-activation trust registry

Provision a root-controlled, read-only JSON registry at the absolute path set by `MCIAS_AUTHORIZATION_REGISTRY`. Never expose this file through an HTTP endpoint. Example shape (all values illustrative, not approvals):

```json
{
  "trusted_heads": {"<organization-id>": {"<approved-head-user-id>": "<ed25519-public-key-hex>"}},
  "approvals": {"<authorization-id>": {"rule_id": "<rule-id>", "authorization_id": "<authorization-id>", "signature": "<ed25519-signature-hex>"}}
}
```

Sign the canonical UTF-8 JSON payload produced by `mcias.production_authorization.signed_payload(rule, approval, source)` using the authorized organization's head private key. The signature binds the rule, authorization, organization, approver and archived source SHA-256. Before trusting the record, a human must independently verify that the signer's authority is current and that the source hash corresponds to the actual encrypted document. A database record alone is never proof of authority. Production activation fails closed if registry is missing, malformed, symlinked, mismatched, or signature invalid.

This is an application verification control, **not evidence** that real head signatures or real keys have been provisioned. The production key registry, certificate deployment and off-host audit custody require a separate deployment acceptance drill.
