FROM python:3.12-slim

WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Create isolated environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt .

# Install ONLY what's in requirements.txt (clean environment)
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

CMD ["python", "app.py"]
