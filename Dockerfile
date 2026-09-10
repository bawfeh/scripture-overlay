FROM python:3.12-slim

# Application directory inside container
WORKDIR /app

# Install Python dependencies first
# This allows Docker to cache this layer when application code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python application files
COPY *.py .

# Copy application directories (if no volume mounted)
# COPY templates ./templates
# COPY static ./static

# Optional application directories (if no volume mounted)
# COPY data ./data
# COPY debug ./debug

# Flask application listens on 8080
EXPOSE 8080

# Start Flask when the container starts
CMD ["python", "app.py"]