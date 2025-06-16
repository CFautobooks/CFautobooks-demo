from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from io import BytesIO
from reportlab.pdfgen import canvas
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from jose import JWTError, jwt

from backend.database import get_db
from backend.models.user import User
from backend.schemas import InvoiceCreate
from backend.utils.security import settings

router = APIRouter(prefix="/invoices", tags=["invoices"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
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
        line = f"{item.description} x{item.quantity} @ ${item.unit_price:.2f}"
        pdf.drawString(100, y, line)
    pdf.showPage()
    pdf.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    message = Mail(
        from_email=settings.FROM_EMAIL,
        to_emails=inv.client_email,
        subject="Your CF AutoBooks Invoice",
        html_content="<p>Please find your invoice attached.</p>"
    )

    encoded = base64.b64encode(pdf_bytes).decode()
    attachment = Attachment(
        FileContent(encoded),
        FileName("invoice.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )
    message.add_attachment(attachment)

    response = sg.send(message)
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send invoice email")

    return {"status": "sent"}

