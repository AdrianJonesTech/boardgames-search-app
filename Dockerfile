# Dockerfile for Board Games Search App (Django)
# Lightweight Python base image
FROM python:3.12-slim

# Environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set work directory
WORKDIR /app

# System packages needed to compile lxml and Pillow-like libs if added later
# Also includes curl for debugging/healthchecks if desired
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Copy dependency list and install Python dependencies via requirements.txt for better caching
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Copy project code
COPY . /app

# Collect static files for production (served by WhiteNoise)
RUN python manage.py collectstatic --noinput

# Expose Django/Gunicorn port
EXPOSE 8000

# Default command: run migrations then start gunicorn
# Note: SQLite DB will be created inside the container filesystem
CMD ["/bin/sh", "-c", "python manage.py migrate --noinput && gunicorn boardgames.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
