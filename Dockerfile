# Use official Python 3.12 slim image
FROM python:3.12-slim

# Install uv for fast package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy dependency files first for layer caching
COPY pyproject.toml requirements.txt ./

# Install dependencies using uv into system site-packages
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application source code
COPY . .

# Create logs and data directories if they don't exist
RUN mkdir -p logs data

# Default command to start the bot
CMD ["python", "main.py"]
