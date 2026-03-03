FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir requests numpy

COPY sales_generator.py .

ENV API_URL=http://backend:8000/api/v1/sales/ingest

CMD ["python", "sales_generator.py"]
