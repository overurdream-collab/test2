"""Fail-closed file-type identification; not a malware antivirus replacement."""
import io
import zipfile
from pathlib import PurePath

MAX_BYTES = 20 * 1024 * 1024
MAX_UNCOMPRESSED = 80 * 1024 * 1024

class UnsafeDocument(ValueError):
    pass

def identify(data: bytes, filename: str) -> str:
    if not data or len(data) > MAX_BYTES:
        raise UnsafeDocument("empty or oversized source")
    suffix = PurePath(filename).suffix.lower()
    if suffix == ".pdf" and data.startswith(b"%PDF-"):
        return "pdf"
    if suffix == ".png" and data.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        return "image"
    if suffix in (".jpg", ".jpeg") and data.startswith(b"\\xff\\xd8\\xff"):
        return "image"
    if suffix == ".csv":
        if b"\\x00" in data:
            raise UnsafeDocument("binary CSV")
        return "csv"
    if suffix == ".xlsx" and zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > 10000 or sum(m.file_size for m in members) > MAX_UNCOMPRESSED:
                raise UnsafeDocument("oversized spreadsheet archive")
            if any(m.filename.startswith("/") or ".." in m.filename.split("/") for m in members):
                raise UnsafeDocument("unsafe archive member")
            if "xl/workbook.xml" not in archive.namelist() or "[Content_Types].xml" not in archive.namelist():
                raise UnsafeDocument("invalid spreadsheet structure")
            if any("vbaProject" in m.filename or "externalLinks/" in m.filename for m in members):
                raise UnsafeDocument("active or external spreadsheet content")
        return "xlsx"
    raise UnsafeDocument("unsupported or mismatched file type")
