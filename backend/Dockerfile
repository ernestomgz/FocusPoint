FROM python:3.12-slim

# System deps for WeasyPrint (cairo, pango, gdk-pixbuf) and general
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libpango-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libpangocairo-1.0-0 libjpeg62-turbo libxml2 libxslt1.1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# App source
COPY app /app/app

ENV PYTHONUNBUFFERED=1
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
