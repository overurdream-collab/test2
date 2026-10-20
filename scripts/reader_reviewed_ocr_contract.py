"""Reviewed OCR Evidence v1: transcription-only integration contract (synthetic pilot).

No authority to attest medical service, tariff, financial eligibility, or G2 trusted rows.
This file does not add production ORM tables or alter A1/G2/Shared Audit.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

TRANSCRIPTION_STATES = (
 "UNVERIFIED_OCR_CANDIDATE", "PENDING_HUMAN_REVIEW", "TRANSCRIPTION_ACCEPTED",
 "TRANSCRIPTION_CORRECTED", "REJECTED", "UNRESOLVED")
class Strict(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)

class CellLocator(Strict):
    page: int=Field(ge=1,le=1000)
    bbox_pixels: tuple[int,int,int,int]
    @model_validator(mode="after")
    def region(self):
        x0,y0,x1,y1=self.bbox_pixels
        if not (0<=x0<x1<=20000 and 0<=y0<y1<=20000):
            raise ValueError("invalid cell box")
        return self

class VersionRecord(Strict):
    version: int=Field(ge=1)
    operation_id: str=Field(min_length=8,max_length=96)
    audit_event_id: str=Field(min_length=1,max_length=36)
    reviewer_user_id: str=Field(min_length=1,max_length=36)
    from_state: str
    to_state: Literal["PENDING_HUMAN_REVIEW","TRANSCRIPTION_ACCEPTED",
                      "TRANSCRIPTION_CORRECTED","REJECTED","UNRESOLVED"]
    corrected_value: str|None=None
    reason_code: str=Field(min_length=1,max_length=64)
    event_id: str=Field(min_length=1,max_length=36)

class ReviewedOCREvidence(Strict):
    schema_version: Literal["mcias.reader.reviewed_ocr_evidence.v1"]="mcias.reader.reviewed_ocr_evidence.v1"
    organization_id: str=Field(min_length=1,max_length=36)
    document_id: str=Field(min_length=1,max_length=36)
    job_id: str=Field(min_length=1,max_length=36)
    candidate_id: str=Field(min_length=1,max_length=36)
    original_sha256: str=Field(pattern=r"^[0-9a-f]{64}$")
    row_id: str=Field(min_length=1,max_length=100)
    field_name: Literal["id","code","unit","qty","price","total"]
    locator: CellLocator
    ocr_value: str
    uncalibrated_ocr_confidence: int=Field(ge=0,le=100)
    transcription_status: Literal["UNVERIFIED_OCR_CANDIDATE","PENDING_HUMAN_REVIEW",
        "TRANSCRIPTION_ACCEPTED","TRANSCRIPTION_CORRECTED","REJECTED","UNRESOLVED"]
    reviewed_value: str|None=None
    versions: list[VersionRecord]
    source_original_bytes_sha256_checked: bool
    g2_native_rows_verified: Literal[False]=False
    clinical_service_verified: Literal[False]=False
    tariff_verified: Literal[False]=False
    financial_eligibility_verified: Literal[False]=False
    a1_trusted_input_eligible: Literal[False]=False
    financial_decision: Literal["NOT_AUTHORIZED"]="NOT_AUTHORIZED"

    @model_validator(mode="after")
    def review_chain(self):
        if self.versions:
            if any(v.version!=i for i,v in enumerate(self.versions,1)):
                raise ValueError("broken review version sequence")
            if self.transcription_status!=self.versions[-1].to_state:
                raise ValueError("review state differs from last version")
            for i,v in enumerate(self.versions):
                expected=self.versions[i-1].to_state if i else "UNVERIFIED_OCR_CANDIDATE"
                if v.from_state!=expected:
                    raise ValueError("review transition chain invalid")
            if self.transcription_status in ("TRANSCRIPTION_ACCEPTED","TRANSCRIPTION_CORRECTED"):
                if self.reviewed_value is None:
                    raise ValueError("missing attested transcription")
        elif self.transcription_status!="UNVERIFIED_OCR_CANDIDATE" or self.reviewed_value is not None:
            raise ValueError("unreviewed OCR cannot be marked reviewed")
        return self
