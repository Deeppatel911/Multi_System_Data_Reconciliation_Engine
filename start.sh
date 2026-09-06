#!/bin/bash

# 1. Start the LiteLLM proxy in the background
echo "Starting LiteLLM Proxy..."
litellm --config litellm_config.yaml --port 4000 &

# Give the proxy 3 seconds to fully boot and bind to the port
sleep 3

# 2. Start the FastAPI server in the foreground
echo "Starting FastAPI Server..."
exec uvicorn server:app --host 0.0.0.0 --port 8000