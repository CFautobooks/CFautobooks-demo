from fastapi import FastAPI
from backend.core.database import Base, engine
from backend.routers import auth, user, invoice

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks API")

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(invoice.router)
