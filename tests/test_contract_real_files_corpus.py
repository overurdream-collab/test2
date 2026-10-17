"""Twenty REAL synthesized source files (PDF/XLSX/scans), not model mockups.

The result here is parser/source-provenance safety, NOT AI Precision/Recall.
All files are generated in memory, carry SYN-only facts, and are never uploaded.
"""
from io import BytesIO
from hashlib import sha256
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from openpyxl import Workbook
from PIL import Image, ImageDraw
import pytest

from mcias.ingestion.reader_agent import read

SYNTHETIC_PRICES = (
    ("H1", "CONSULT", 5000),
    ("H2", "CONSULT", 7000),
    ("H3", "CONSULT", 6000),
)

def pdf_document(pages):
    buffer=BytesIO()
    pdf=canvas.Canvas(buffer, pagesize=(612,792))
    for index, lines in enumerate(pages,1):
        pdf.setFont("Helvetica",11)
        pdf.drawString(35,750,"SYNTHETIC DOCUMENT PAGE "+str(index))
        for line_no,line in enumerate(lines):
            pdf.drawString(35,700-24*line_no,line)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()

def price_workbook(version):
    workbook=Workbook()
    ws=workbook.active
    ws.title="SYN-TARIFF"
    ws.append(["provider","service","amount","currency","valid_from","valid_until"])
    for provider,service,amount in SYNTHETIC_PRICES:
        ws.append([provider,service,amount+version,"YER","2026-01-01","2027-01-01"])
    payload=BytesIO()
    workbook.save(payload)
    return payload.getvalue()

def scanned_pdf(text):
    image=Image.new("RGB",(1250,1750),"white")
    pen=ImageDraw.Draw(image)
    pen.text((50,140),text,fill="black")
    buffer=BytesIO()
    pdf=canvas.Canvas(buffer)
    pdf.drawImage(ImageReader(image),0,0,width=600,height=780)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()

@pytest.mark.parametrize("case_index",range(10),ids=lambda i:"SYN-3PAGE-PDF-"+str(i+1))
def test_ten_three_page_actual_pdf_contracts_are_separately_anchored(case_index):
    pages=[
        ["SYN agreement "+str(case_index), "Effective 2026-01-01 to 2027-01-01"],
        [f"H1 CONSULT tariff {5000+case_index} YER", "H2 CONSULT tariff 7000 YER"],
        ["Excluded: medical treatment outside the country", "Signed source pending review"],
    ]
    source=pdf_document(pages)
    assert sha256(source).hexdigest()
    result=read(source,"SYN-contract-"+str(case_index)+".pdf")
    assert result.format=="pdf"
    assert result.units_total==3 and result.units_processed==3
    assert [r.locator.index for r in result.records]==[1,2,3]
    assert str(5000+case_index) in result.records[1].values["text"]
    assert "7000" in result.records[1].values["text"]
    assert "Excluded" in result.records[2].values["text"]

@pytest.mark.parametrize("version",range(5),ids=lambda i:"SYN-THREE-PROVIDER-"+str(i+1))
def test_five_actual_xlsx_documents_keep_three_provider_prices_in_distinct_rows(version):
    file_data=price_workbook(version)
    result=read(file_data,"SYN-prices-"+str(version)+".xlsx")
    assert result.format=="xlsx" and result.units_processed==3
    rows=result.records
    assert [(r.locator.row,r.values["provider"],r.values["amount"]) for r in rows]==[
        (2,"H1",str(5000+version)),(3,"H2",str(7000+version)),
        (4,"H3",str(6000+version))]
    assert all(r.values["currency"]=="YER" for r in rows)
    assert len(set((r.locator.index,r.locator.row) for r in rows))==3

@pytest.mark.parametrize("case_index",range(5),ids=lambda i:"SYN-UNREVIEWED-SCAN-"+str(i+1))
def test_five_actual_scanned_pdf_sources_never_auto_accept_without_local_ocr(monkeypatch,case_index):
    monkeypatch.delenv("MCIAS_LOCAL_OCR",raising=False)
    raw=scanned_pdf("SYN NO PATIENT DATA H"+str(case_index)+" CONSULT 5000 YER")
    result=read(raw,"SYN-scanned-"+str(case_index)+".pdf")
    assert result.format=="pdf"
    assert result.units_total==1 and result.units_processed==0
    assert len(result.quarantined)==1
    assert result.records==[]
