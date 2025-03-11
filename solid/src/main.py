import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from loguru import logger
import uvicorn

# Local imports
from .routes.auth_routes import auth_router
from .routes.pod_routes import pod_router
from .utils.exceptions import ApiError

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Solid Pod Server",
    description="A Python implementation of a Solid Pod server using Inrupt's Solid client libraries",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(pod_router, prefix="/api/pod", tags=["Pod Management"])

# Exception handler for ApiError
@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    logger.error(f"{exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "status": exc.status_code,
            }
        },
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}

def start():
    """Start the Solid Pod server"""
    port = int(os.getenv("PORT", "3000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting Solid Pod Server on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT", "development") == "development",
    )

if __name__ == "__main__":
    start() 