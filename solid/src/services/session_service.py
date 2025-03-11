import uuid
from typing import Dict, Optional, Any
from http import HTTPStatus
import httpx
import json
from datetime import datetime, timedelta

from ..middleware.auth_middleware import Session
from ..utils.exceptions import ApiError
from ..utils.logger import logger

class SessionService:
    """Service for managing user sessions"""
    
    def __init__(self):
        """Initialize the session service with an in-memory session store"""
        # In-memory session storage (for demo purposes)
        # In production, use a proper session store like Redis
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    async def create_session(self) -> str:
        """
        Create a new session
        
        Returns:
            str: The session ID
        """
        session_id = str(uuid.uuid4())
        
        self._sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "is_logged_in": False,
            "web_id": None,
            "oidc_issuer": None,
            "tokens": None,
        }
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID
        
        Args:
            session_id: The session ID
            
        Returns:
            Session: The session object
            
        Raises:
            ApiError: If the session is not found
        """
        if session_id not in self._sessions:
            raise ApiError("Invalid session ID", HTTPStatus.BAD_REQUEST)
        
        session_data = self._sessions[session_id]
        
        # Create a fetch function for the session
        # This is a simplified implementation
        async def fetch(url: str, options: Dict[str, Any] = None) -> httpx.Response:
            """
            Fetch a resource with the session's credentials
            
            Args:
                url: The URL to fetch
                options: Fetch options
                
            Returns:
                Response: The HTTP response
            """
            options = options or {}
            headers = options.get("headers", {})
            
            # Add authorization header if we have tokens
            if session_data.get("tokens"):
                headers["Authorization"] = f"Bearer {session_data['tokens']['access_token']}"
            
            # Merge headers
            options["headers"] = headers
            
            # Make the request
            async with httpx.AsyncClient() as client:
                method = options.get("method", "GET").lower()
                
                if method == "get":
                    return await client.get(url, **options)
                elif method == "post":
                    return await client.post(url, **options)
                elif method == "put":
                    return await client.put(url, **options)
                elif method == "delete":
                    return await client.delete(url, **options)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Create the session object
        return Session(
            session_id=session_id,
            is_logged_in=session_data.get("is_logged_in", False),
            web_id=session_data.get("web_id"),
            fetch=fetch,
        )
    
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """
        Update a session
        
        Args:
            session_id: The session ID
            data: The data to update
            
        Raises:
            ApiError: If the session is not found
        """
        if session_id not in self._sessions:
            raise ApiError("Invalid session ID", HTTPStatus.BAD_REQUEST)
        
        # Update the session data
        self._sessions[session_id].update(data)
    
    async def delete_session(self, session_id: str) -> None:
        """
        Delete a session
        
        Args:
            session_id: The session ID
            
        Raises:
            ApiError: If the session is not found
        """
        if session_id not in self._sessions:
            raise ApiError("Invalid session ID", HTTPStatus.BAD_REQUEST)
        
        # Delete the session
        del self._sessions[session_id] 