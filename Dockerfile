FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for psycopg and standard building
RUN apt-get update && apt-get install -y gcc libpq-dev libpq5 && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker layer caching
COPY requirements.txt .

# 1. Install LiteLLM Proxy FIRST (so its strict bounds don't ruin our app later)
RUN pip install --no-cache-dir 'litellm[proxy]'

# 2. Install main requirements
RUN pip install --no-cache-dir -r requirements.txt

# 3. THE SILVER BULLET: Force upgrade the MCP SDK to get 'request_state'
RUN pip install --no-cache-dir --upgrade mcp fastmcp

# Copy the entire application code into the container
COPY . .

# Make the startup script executable
RUN chmod +x /app/start.sh

# Expose ports for both FastAPI and LiteLLM
EXPOSE 8000
EXPOSE 4000

# Execute the wrapper script
CMD ["/app/start.sh"]