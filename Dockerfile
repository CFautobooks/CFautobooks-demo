# syntax=docker/dockerfile:1
FROM python:3.10-slim

WORKDIR /app

# copy everything
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/

# set env
ENV PYTHONPATH=/app/backend
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
