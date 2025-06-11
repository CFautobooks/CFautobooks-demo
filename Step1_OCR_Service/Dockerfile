FROM python:3.10-slim

WORKDIR /app

# Install system deps for pillow & Tesseract
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      tesseract-ocr libtesseract-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY main.py .

# Expose and run
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
