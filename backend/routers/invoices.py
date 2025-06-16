from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from reportlab.pdfgen import canvas
from io import BytesIO
import base64
import sendgrid
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

from .. import schemas, models
from ..database import get_db
from ..utils.auth import create_access_token, verify_password  # for token decode if needed
from jose import jwt, JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
router = APIRouter(tags=["invoices"], prefix="/invoices")

def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    try:
        payload = jwt.decode(token, ... )  # use SECRET_KEY & ALGORITHM from auth.py
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(401, "Invalid token")
    user = db.query(models.User).filter(models.User.email==email).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user

@router.post("/send")
def send_invoice(inv: schemas.InvoiceCreate, user=Depends(get_current_user)):
    # generate PDF
    buf = BytesIO(); c = canvas.Canvas(buf); y=800
    c.drawString(100, y, f"Invoice for {inv.client_email}")
    for i in inv.items:
        y -= 20
        c.drawString(100, y, f"{i.description} x{i.quantity} @ {i.unit_price}")
    c.showPage(); c.save()
    pdf = buf.getvalue(); buf.close()

    # email via SendGrid
    sg = sendgrid.SendGridAPIClient("YOUR_SENDGRID_KEY")
    msg = Mail(
      from_email="you@domain.com", to_emails=inv.client_email,
      subject="Your CF AutoBooks Invoice", html_content="<p>See attached</p>"
    )
    encoded = base64.b64encode(pdf).decode()
    attach = Attachment(FileContent(encoded), FileName("invoice.pdf"),
                        FileType("application/pdf"), Disposition("attachment"))
    msg.attachment = attach
    resp = sg.send(msg)
    if resp.status_code >= 400:
        raise HTTPException(500, "Failed to send email")
    return {"status": "sent"}
