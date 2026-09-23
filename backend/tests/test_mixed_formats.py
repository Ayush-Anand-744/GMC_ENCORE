from io import BytesIO
from pathlib import Path
from datetime import date
from email.message import EmailMessage
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from docx import Document
from backend.orchestration.orchestrator import Orchestrator


def test_excel_pdf_image_email_word_batch():
    fixtures=Path(__file__).parent/'fixtures'
    pdf=BytesIO()
    c=canvas.Canvas(pdf)
    c.drawString(50,730,'Air Ambulance: Covered')
    c.save()
    doc=Document();doc.add_paragraph('Health Check-Up: Covered')
    word=BytesIO();doc.save(word)
    msg=EmailMessage();msg['Subject']='RFQ extra terms';msg.set_content('Road Ambulance: Covered')
    image=Image.new('RGB',(1000,180),'white');d=ImageDraw.Draw(image)
    try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',36)
    except OSError:font=None
    d.text((35,50),'LASIK Surgery Covered',font=font,fill='black')
    png=BytesIO();image.save(png,format='PNG')
    files=[('Employee_Data_Sample.xlsx',(fixtures/'Employee_Data_Sample.xlsx').read_bytes()),
           ('RFQ_Sample.xlsx',(fixtures/'RFQ_Sample.xlsx').read_bytes()),
           ('extra.pdf',pdf.getvalue()),('additional.docx',word.getvalue()),
           ('brokermail.eml',msg.as_bytes()),('photo.png',png.getvalue())]
    output=Orchestrator().process(files,date(2026,9,22))
    assert len(output['classifications'])==6
    assert len(output['demography'])==36
    assert output['summary']['demo_lives']==36
    assert len(output['extracted_data'])>90
    assert {'extra.pdf','additional.docx','brokermail.eml','photo.png'}.issubset({r['File'] for r in output['extracted_data']})
