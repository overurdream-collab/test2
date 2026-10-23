"""Watermarked PDF invoice fixtures; not real invoices or evidence of payment."""
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def invoice_pdf(lines):
    if not lines or any(not str(row['invoice_reference']).startswith('SYN-') for row in lines):
        raise ValueError('Synthetic invoice references must start with SYN-')
    output=BytesIO();pdf=canvas.Canvas(output,pagesize=A4,invariant=1)
    for row in lines:
        pdf.setFont('Helvetica-Bold',17);pdf.drawString(40,800,'SYNTHETIC INVOICE - NOT A REAL INVOICE')
        pdf.setFont('Helvetica',11);y=760
        for key in ('invoice_reference','beneficiary','provider','service','service_date','gross','copay','net','currency'):
            pdf.drawString(40,y,f'{key}: {row.get(key, "SYN-NOT-PROVIDED")}');y-=24
        pdf.drawString(40,450,'Test fixture only. No payment, signature or institutional approval.')
        pdf.showPage()
    pdf.save();return output.getvalue()
