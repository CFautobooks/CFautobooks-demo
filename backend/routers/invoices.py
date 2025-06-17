from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.schemas import Invoice
from backend.core.database import get_db
from backend.models.invoice import Invoice as InvoiceModel

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
)

@router.post("/", response_model=Invoice, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: Invoice, db: Session = Depends(get_db)):
    inv = InvoiceModel(total=payload.total)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv

@router.get("/", response_model=List[Invoice])
def read_invoices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(InvoiceModel).offset(skip).limit(limit).all()

@router.get("/{invoice_id}", response_model=Invoice)
def read_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.query(InvoiceModel).get(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv
