# Multi-stage production container for MantaBooking
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \n    DATA_DIR=/app/data

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Persistent SQLite data (mount a volume here so data survives container restarts)
VOLUME ["/app/data"]

# Expose port (Render/Heroku/Fly.io injects PORT at runtime)
EXPOSE 5000

# Run with production WSGI server
CMD ["sh", "-c", "gunicorn -w 2 --threads 4 --timeout 120 -b 0.0.0.0:${PORT:-5000} server:app"]
