FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (needed for psycopg2 and others)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set Flask application
ENV FLASK_APP=run.py

# Expose port
EXPOSE 5000

# Command to run the app
CMD ["flask", "run", "--host=0.0.0.0"]

