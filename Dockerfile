# ==========================================
# STAGE 1: Builder
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# ==========================================
# STAGE 2: Runner
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime database dependencies
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

# Copy wheels from the builder stage and install them
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# NEW: Install LiteLLM Proxy sequentially to bypass dependency resolver conflicts
RUN pip install --no-cache 'litellm[proxy]'

# Copy the entire application code into the container
COPY . .

# Make the startup script executable
RUN chmod +x /app/start.sh

# Expose ports for both FastAPI and LiteLLM
EXPOSE 8000
EXPOSE 4000

# Execute the wrapper script
CMD ["/app/start.sh"]
