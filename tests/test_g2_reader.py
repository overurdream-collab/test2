import io
import zipfile
import pytest
from openpyxl import Workbook
from pypdf import PdfWriter
from mcias.ingestion.reader_agent import read
from mcias.ingestion.file_scanner import identify, UnsafeDocument
from mcias.ingestion.palermo.palermo_1 import review

def test_csv_source_provenance_and_coverage():
    result=read(b"claim,amount\nA,12\nB,20\n","batch.csv")
    assert len(result.records)==2
    assert result.records[0].locator.row==2
    assert result.records[1].values["amount"]=="20"
    assert review(result)["coverage"]["complete"]

def test_csv_bad_row_is_quarantined_without_losing_good_row():
    result=read(b"claim,amount\nA,12\nB\n","batch.csv")
    assert len(result.records)==1
    assert result.quarantined[0]["locator"]["kind"]=="row"
    assert review(result)["status"]=="review_required"

def test_xlsx_real_workbook_with_provenance():
    book=Workbook()
    sheet=book.active
    sheet.append(["claim","amount"])
    sheet.append(["A",12])
    out=io.BytesIO();book.save(out)
    result=read(out.getvalue(),"claims.xlsx")
    assert result.records[0].locator.index==1
    assert result.records[0].locator.row==2
    assert result.records[0].values["amount"]=="12"

def test_pdf_scanned_page_is_quarantined_with_page_number():
    writer=PdfWriter();writer.add_blank_page(width=300,height=300)
    out=io.BytesIO();writer.write(out)
    result=read(out.getvalue(),"scanned.pdf")
    assert result.quarantined[0]["locator"]=={"kind":"page","index":1}
    assert result.complete
    assert review(result)["status"]=="review_required"

def test_malformed_excel_is_rejected():
    with pytest.raises(UnsafeDocument):
        read(b"not an excel workbook","broken.xlsx")

def test_file_type_mismatch_rejected():
    with pytest.raises(UnsafeDocument):
        identify(b"%PDF-1.7", "invoice.xlsx")

def test_image_requires_local_ocr_and_is_quarantined():
    result=read(b"\x89PNG\r\n\x1a\n"+b"synthetic","scan.png")
    assert result.quarantined and result.units_total==1
