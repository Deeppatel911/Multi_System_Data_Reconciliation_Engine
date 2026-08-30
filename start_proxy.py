import os
import subprocess
from dotenv import load_dotenv

# 1. Force Python to load the .env file into the system environment
load_dotenv()

# 2. Force UTF-8 encoding for the Windows terminal banner
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

print("Starting LiteLLM Gateway...")

# 3. Launch LiteLLM with the loaded environment variables
try:
    subprocess.run(["litellm", "--config", "litellm_config.yaml"], env=env)
except KeyboardInterrupt:
    print("\nShutting down LiteLLM Gateway...")
