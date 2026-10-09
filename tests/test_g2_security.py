"""ReaderAgent boundary and security regressions."""
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from mcias.app import app
from mcias.ingestion.file_scanner import identify, UnsafeDocument, MAX_BYTES
from mcias.ingestion.reader_agent import read

def test_upload_without_auth_is_rejected():
    response=TestClient(app).post("/api/v1/ingestion/uploads?filename=claims.csv",content=b"id\n1\n")
    assert response.status_code==401

def test_reject_binary_csv():
    with pytest.raises(UnsafeDocument):
        identify(b"id\x00amount","claims.csv")

def test_reject_oversized_source():
    with pytest.raises(UnsafeDocument):
        identify(b"a"*(MAX_BYTES+1),"claims.csv")

def test_xlsx_archive_path_traversal_rejected():
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w") as z:
        z.writestr("[Content_Types].xml","synthetic")
        z.writestr("xl/workbook.xml","synthetic")
        z.writestr("../escape.txt","synthetic")
    with pytest.raises(UnsafeDocument,match="unsafe archive"):
        identify(buffer.getvalue(),"traversal.xlsx")

def test_csv_duplicate_header_rejected():
    with pytest.raises(ValueError,match="header"):
        read(b"id,id\nA,B\n","dup.csv")
