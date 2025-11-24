# Use lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

#Uninstalling requirements.txt first
RUN pip uninstall -y langchain langchain-core langchain-community langchain-experimental langchain-openai || true

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for Flask
EXPOSE 8080

# Run Flask app
CMD ["python", "app.py"]


