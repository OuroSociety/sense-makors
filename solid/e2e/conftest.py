import os
import pytest
import requests
import time
import subprocess
import signal
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Base URL for the API
API_URL = os.getenv("API_URL", "http://localhost:3000")

@pytest.fixture(scope="session", autouse=True)
def server_process():
    """
    Start the server for E2E tests if it's not already running
    """
    # Check if the server is already running
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            # Server is already running, no need to start it
            yield None
            return
    except requests.exceptions.ConnectionError:
        # Server is not running, start it
        pass
    
    # Start the server
    env = os.environ.copy()
    env["ENVIRONMENT"] = "test"
    
    process = subprocess.Popen(
        ["python", "-m", "src.main"],
        env=env,
        cwd=str(Path(__file__).parent.parent),
    )
    
    # Wait for the server to start
    max_retries = 10
    retries = 0
    while retries < max_retries:
        try:
            response = requests.get(f"{API_URL}/health")
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        
        time.sleep(1)
        retries += 1
    
    # Yield control back to the tests
    yield process
    
    # Stop the server after tests
    if process:
        process.send_signal(signal.SIGTERM)
        process.wait() 