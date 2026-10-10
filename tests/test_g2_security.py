import pytest
pytestmark = pytest.mark.usefixtures("limiter_database")
"""ReaderAgent boundary and security regressions."""
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from mcias.app import app, get_db
from mcias.ingestion.file_scanner import identify, UnsafeDocument, MAX_BYTES
from mcias.ingestion.reader_agent import read

def test_upload_without_auth_is_rejected():
    app.dependency_overrides[get_db] = lambda: None
    try:
        response=TestClient(app).post("/api/v1/ingestion/uploads?filename=claims.csv",content=b"id\n1\n")
        assert response.status_code==401
    finally:
        app.dependency_overrides.pop(get_db, None)

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

def test_duplicate_zip_members_rejected():
    import warnings
    buffer=io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("[Content_Types].xml", "x")
            z.writestr("xl/workbook.xml", "x")
            z.writestr("xl/workbook.xml", "different")
    with pytest.raises(UnsafeDocument, match="duplicate archive member"):
        identify(buffer.getvalue(), "duplicate.xlsx")

def test_backslash_archive_traversal_rejected():
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("[Content_Types].xml", "x")
        z.writestr("xl/workbook.xml", "x")
        z.writestr(".."+chr(92)+"outside.txt", "x")
    with pytest.raises(UnsafeDocument, match="unsafe archive"):
        identify(buffer.getvalue(), "backslash.xlsx")

def test_excessive_xlsx_compression_rejected():
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "x")
        z.writestr("xl/workbook.xml", "x")
        z.writestr("xl/worksheets/sheet1.xml", "A"*1024*1024)
    with pytest.raises(UnsafeDocument, match="compression ratio"):
        identify(buffer.getvalue(), "compressed.xlsx")
