from fastapi import Depends, Header, HTTPException
from http import HTTPStatus
from typing import Optional, Dict, Any
from pydantic import BaseModel

from ..services.session_service import SessionService
from ..utils.exceptions import ApiError
from ..utils.logger import logger

# Create session service instance
session_service = SessionService()

class Session(BaseModel):
    """Session model for authenticated users"""
    session_id: str
    is_logged_in: bool
    web_id: Optional[str] = None
    fetch: Any = None  # This would be a function in a real implementation

async def get_session(authorization: Optional[str] = Header(None)) -> Session:
    """
    Get the session from the Authorization header
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Session: The session object
        
    Raises:
        ApiError: If authentication fails
    """
    if not authorization:
        logger.error("Authentication required")
        raise ApiError("Authentication required", HTTPStatus.UNAUTHORIZED)
    
    if not authorization.startswith("Bearer "):
        logger.error("Invalid authorization format")
        raise ApiError("Invalid authorization format", HTTPStatus.UNAUTHORIZED)
    
    session_id = authorization.split(" ")[1]
    
    try:
        session = await session_service.get_session(session_id)
        
        if not session or not session.is_logged_in:
            logger.error(f"Invalid or expired session: {session_id}")
            raise ApiError("Invalid or expired session", HTTPStatus.UNAUTHORIZED)
        
        return session
    except ApiError:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise ApiError("Authentication failed", HTTPStatus.UNAUTHORIZED) 