FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for psycopg and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libffi-dev libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn kyisa_cms.wsgi --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120"]
