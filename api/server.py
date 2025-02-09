import uvicorn
from app import app

def start_api(host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI server using uvicorn"""
    uvicorn.run(
        "api.app:app",
        host=host,
        port=port,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )

if __name__ == "__main__":
    start_api() 