FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port (Render sets PORT environment variable dynamically)
EXPOSE 8000

# Start application using uvicorn via shell to expand the $PORT env variable
CMD uvicorn backend.app:app --host 0.0.0.0 --port $PORT
