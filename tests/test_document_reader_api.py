"""Synthetic API permission and G2 custody tests, without a production database."""
import hashlib
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Response

from mcias.ingestion import api
from mcias.models import SourceFile
from mcias.models_ingestion import IngestionDocument


class MemorySession:
    def __init__(self, document, source, job, quarantine=()):
        self.document = document
        self.source = source
        self.job = job
        self.quarantine = list(quarantine)

    def get(self, model, identifier):
        if model is IngestionDocument:
            return self.document
        if model is SourceFile:
            return self.source
        return None

    def scalar(self, statement):
        return self.job

    def scalars(self, statement):
        return SimpleNamespace(all=lambda: self.quarantine)


class ReaderPreviewApiTests(unittest.TestCase):
    def setUp(self):
        self.raw = b"%PDF-synthetic-invoice"
        self.sha = hashlib.sha256(self.raw).hexdigest()
        self.document = SimpleNamespace(id="SYN-DOC", source_id="SYN-SOURCE",
            organization_id="SYN-ORG", status="extracted", filename="invoice.pdf", sha256=self.sha)
        self.source = SimpleNamespace(storage_key="a" * 48, sha256=self.sha)
        self.job = SimpleNamespace(id="SYN-JOB", status="extracted",
                                   manifest={"format": "pdf", "complete": True})
        self.db = MemorySession(self.document, self.source, self.job)
        self.user = SimpleNamespace(id="SYN-USER", organization_id="SYN-ORG")

    def _call(self, *, org=True, field=True):
        def require_org(db, actor, organization, permission):
            if not org or actor.organization_id != organization:
                raise HTTPException(403, "forbidden")
        def require_field(db, actor, organization, name):
            self.assertEqual(name, "text")
            if not field:
                raise HTTPException(403, "forbidden")
        with patch.dict(os.environ, {"MCIAS_DOCUMENT_READER_MODE": "local_preview",
                                         "MCIAS_STORAGE_KEY": bytes(range(32)).hex(),
                                         "MCIAS_STORAGE_DIR": "/tmp/synthetic-reader"}), patch.object(
            api, "resolve_user", return_value=(self.user, None)
        ), patch.object(api, "require_organization", side_effect=require_org), patch.object(
            api, "require_sensitive_field", side_effect=require_field
        ), patch.object(api, "EncryptedStore") as store, patch.object(
            api, "isolated_preview_pdf", return_value={"status": "HUMAN_REVIEW"}
        ) as reader:
            store.return_value.get.return_value = self.raw
            response = Response()
            try:
                value = api.document_reader_preview("SYN-DOC", response, db=self.db)
            except HTTPException as exc:
                return exc.status_code, reader.call_count, store.return_value.get.call_count
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(value["status"], "HUMAN_REVIEW")
            reader.assert_called_once_with(self.raw, self.document.id, self.sha)
            return 200, reader.call_count, store.return_value.get.call_count

    def test_preview_requires_both_tenant_access_and_medical_text_grant(self):
        self.assertEqual(self._call(org=False), (403, 0, 0))
        self.assertEqual(self._call(field=False), (403, 0, 0))
        self.assertEqual(self._call(), (200, 1, 1))

    def test_other_organization_never_fetches_original(self):
        self.user.organization_id = "SYN-OTHER"
        self.assertEqual(self._call(), (403, 0, 0))

    def test_unverified_g2_scan_failure_does_not_enter_reader(self):
        self.document.status = "review_required"
        self.job.status = "review_required"
        self.job.manifest = {"error": "MalwareScannerUnavailable", "complete": False}
        self.assertEqual(self._call(), (409, 0, 0))

    def test_tampered_metadata_source_digest_blocks_previews(self):
        self.source.sha256 = "0" * 64
        self.assertEqual(self._call(), (409, 0, 0))


if __name__ == "__main__":
    unittest.main()
