from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from io import BytesIO
from reportlab.pdfgen import canvas
import base64
import sendgrid
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from jose import JWTError, jwt

from core.database import get_db
from models.user import User
from schemas import InvoiceCreate
from utils.security import settings

router = APIRouter(prefix="/invoices", tags=["invoices"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/send", status_code=status.HTTP_201_CREATED)
def send_invoice(inv: InvoiceCreate, user: User = Depends(get_current_user)):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    y = 800
    pdf.drawString(100, y, f"Invoice for {inv.client_email}")
    for item in inv.items:
        y -= 20
        pdf.drawString(100, y, f"{item.description} x{item.quantity} @ ${item.unit_price:.2f}")
    pdf.showPage(); pdf.save()
    pdf_bytes = buffer.getvalue(); buffer.close()

    sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    msg = Mail(
        from_email=settings.FROM_EMAIL,
        to_emails=inv.client_email,
        subject="Your CF AutoBooks Invoice",
        html_content="<p>Please find your invoice attached.</p>"
    )
    encoded = base64.b64encode(pdf_bytes).decode()
    attach = Attachment(
        FileContent(encoded),
        FileName("invoice.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )
    msg.attachment = attach
    resp = sg.send(msg)
    if resp.status_code >= 400:
        raise HTTPException(status_code=500, detail="Failed to send invoice email")
    return {"status": "sent"}
