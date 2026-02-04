# Use official Python 3.10 slim image for smaller size
FROM python:3.10-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: prevents python from writing pyc files to disc
# PYTHONUNBUFFERED: ensures python output is sent straight to terminal (logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
# For simple bots, slim is often enough, but sometimes we need curl/build-essential
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (for efficient layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create directory for data if it doesn't exist (though strictly readonly in some containers, usually fine in Railway)
RUN mkdir -p data

# Run the bot
CMD ["python", "bot.py"]
