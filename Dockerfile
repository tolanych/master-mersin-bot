# ================================
# Dockerfile — Container Config
# ================================

FROM python:3.12-slim

RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lib/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8008

# Run bot
CMD ["python", "main.py"]
