from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from schemas import Invoice
from models.invoice import Invoice as DBInvoice

invoices_router = APIRouter()

@invoices_router.get("/", response_model=list[Invoice])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(DBInvoice).all()