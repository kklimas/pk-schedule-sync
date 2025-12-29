# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Warsaw

# Set timezone
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files individually
COPY app ./app
COPY ui ./ui
COPY main.py .
COPY .env-docker .env
COPY google-calendar-key.json .

COPY gunicorn_conf.py .

# Expose port
EXPOSE 8000

# Run the application using Gunicorn for production
CMD ["gunicorn", "-c", "gunicorn_conf.py", "main:app"]
