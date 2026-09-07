FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for psycopg and standard building
RUN apt-get update && apt-get install -y gcc libpq-dev libpq5 && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install all main dependencies directly (No brittle wheel stage!)
RUN pip install --no-cache-dir -r requirements.txt

# Install LiteLLM Proxy sequentially to prevent dependency conflicts
RUN pip install --no-cache-dir 'litellm[proxy]'

# Copy the entire application code into the container
COPY . .

# Make the startup script executable
RUN chmod +x /app/start.sh

# Expose ports for both FastAPI and LiteLLM
EXPOSE 8000
EXPOSE 4000

# Execute the wrapper script
CMD ["/app/start.sh"]