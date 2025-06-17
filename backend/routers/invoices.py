from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from schemas import InvoiceCreate, InvoiceResponse, InvoiceAdmin  # ← import from schemas.py at repo root
from core.database import get_db
from models.invoice import Invoice

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post("/", response_model=InvoiceResponse)
def create_invoice(invoice_in: InvoiceCreate, db: Session = Depends(get_db)):
    invoice = Invoice(
        owner_id=invoice_in.owner_id,
        filename=invoice_in.filename,
        status="PENDING",
        total_amount=invoice_in.total_amount
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice

@router.get("/", response_model=list[InvoiceResponse])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).all()

@router.get("/admin", response_model=list[InvoiceAdmin])
def admin_list(db: Session = Depends(get_db)):
    return db.query(Invoice).all()
