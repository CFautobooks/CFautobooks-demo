from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    plan = Column(String, nullable=False)           # "DIY", "WHITE_LABEL", "CARMICHAEL"
    stripe_customer_id = Column(String, nullable=True)
