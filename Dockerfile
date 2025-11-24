# Use lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

#Uninstalling requirements.txt first
RUN rm -rf /usr/local/lib/python3.12/site-packages/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for Flask
EXPOSE 8080

# Run Flask app
CMD ["python", "app.py"]




