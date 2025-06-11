from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class InvoiceAdmin(BaseModel):
    id: int
    owner_id: int
    total_amount: Optional[float] = None
    created_at: datetime

    class Config:
        # This tells Pydantic to read data from ORM objects
        orm_mode = True
