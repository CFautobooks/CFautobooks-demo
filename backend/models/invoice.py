from sqlalchemy import Column, Integer, Float, String
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from core.database import Base

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    client_email = Column(String, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
