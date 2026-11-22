FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set working directory to where manage.py is located
WORKDIR /app/ticketSwift

# Run collectstatic during build
ENV DJANGO_SETTINGS_MODULE=ticketSwift.settings.production
ENV SECRET_KEY=build-phase-secret-key-temporary
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# On startup: migrate, seed demo data, and bind to Render's dynamic port
CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_data && gunicorn ticketSwift.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3"]
