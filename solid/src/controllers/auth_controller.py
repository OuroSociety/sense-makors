import os
from typing import Dict, Any, Optional
from http import HTTPStatus
import httpx
import urllib.parse
import uuid
from datetime import datetime

from ..services.session_service import SessionService
from ..utils.exceptions import ApiError
from ..utils.logger import logger

class AuthController:
    """Controller for authentication operations"""
    
    def __init__(self):
        """Initialize the authentication controller"""
        self.session_service = SessionService()
        self.client_name = os.getenv("CLIENT_NAME", "Solid Pod Server")
        self.redirect_url = os.getenv("REDIRECT_URL", "http://localhost:3000/api/auth/callback")
    
    async def login(self, oidc_issuer: str) -> Dict[str, str]:
        """
        Login to a Solid identity provider
        
        Args:
            oidc_issuer: The OIDC issuer URL
            
        Returns:
            Dict: Session ID and login URL
            
        Raises:
            ApiError: If login fails
        """
        if not oidc_issuer:
            raise ApiError("OIDC issuer is required", HTTPStatus.BAD_REQUEST)
        
        try:
            # Create a new session
            session_id = await self.session_service.create_session()
            
            # Update the session with the OIDC issuer
            await self.session_service.update_session(session_id, {
                "oidc_issuer": oidc_issuer,
            })
            
            # Generate state for CSRF protection
            state = str(uuid.uuid4())
            
            # Build the login URL
            # This is a simplified implementation
            # In a real app, you would discover the OIDC endpoints
            params = {
                "client_id": os.getenv("CLIENT_ID", "solid-pod-server"),
                "redirect_uri": f"{self.redirect_url}?session_id={session_id}",
                "response_type": "code",
                "scope": "openid profile",
                "state": state,
            }
            
            login_url = f"{oidc_issuer}/auth?{urllib.parse.urlencode(params)}"
            
            # Store the state in the session
            await self.session_service.update_session(session_id, {
                "state": state,
            })
            
            return {
                "session_id": session_id,
                "login_url": login_url,
            }
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise ApiError(f"Login failed: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
    
    async def register(self, oidc_issuer: str) -> Dict[str, str]:
        """
        Register with a Solid identity provider
        
        Args:
            oidc_issuer: The OIDC issuer URL
            
        Returns:
            Dict: Registration URL and message
            
        Raises:
            ApiError: If registration fails
        """
        if not oidc_issuer:
            raise ApiError("OIDC issuer is required", HTTPStatus.BAD_REQUEST)
        
        try:
            # For most Solid identity providers, registration is handled on their website
            # We'll redirect the user to the provider's registration page
            registration_url = f"{oidc_issuer}/register"
            
            return {
                "registration_url": registration_url,
                "message": "Please complete registration on the identity provider website",
            }
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            raise ApiError(f"Registration failed: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
    
    async def handle_callback(
        self, session_id: str, code: Optional[str], state: Optional[str]
    ) -> Dict[str, Any]:
        """
        Handle callback from Solid identity provider
        
        Args:
            session_id: The session ID
            code: The authorization code
            state: The state parameter
            
        Returns:
            Dict: Success status, Web ID, and session ID
            
        Raises:
            ApiError: If callback handling fails
        """
        if not session_id:
            raise ApiError("Session ID is required", HTTPStatus.BAD_REQUEST)
        
        try:
            # Get the session
            session = await self.session_service.get_session(session_id)
            
            # Verify the state parameter
            session_data = session._sessions[session_id]
            if state != session_data.get("state"):
                raise ApiError("Invalid state parameter", HTTPStatus.BAD_REQUEST)
            
            if not code:
                raise ApiError("Authorization code is required", HTTPStatus.BAD_REQUEST)
            
            # Exchange the code for tokens
            # This is a simplified implementation
            # In a real app, you would use the OIDC endpoints discovered from the issuer
            oidc_issuer = session_data.get("oidc_issuer")
            if not oidc_issuer:
                raise ApiError("OIDC issuer not found in session", HTTPStatus.BAD_REQUEST)
            
            token_url = f"{oidc_issuer}/token"
            
            # Prepare the token request
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{self.redirect_url}?session_id={session_id}",
                "client_id": os.getenv("CLIENT_ID", "solid-pod-server"),
                "client_secret": os.getenv("CLIENT_SECRET", ""),
            }
            
            # Make the token request
            async with httpx.AsyncClient() as client:
                token_response = await client.post(token_url, data=token_data)
                
                if token_response.status_code != HTTPStatus.OK:
                    raise ApiError(
                        f"Token request failed: {token_response.text}",
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                    )
                
                tokens = token_response.json()
            
            # Get the user info
            userinfo_url = f"{oidc_issuer}/userinfo"
            
            async with httpx.AsyncClient() as client:
                userinfo_response = await client.get(
                    userinfo_url,
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                )
                
                if userinfo_response.status_code != HTTPStatus.OK:
                    raise ApiError(
                        f"User info request failed: {userinfo_response.text}",
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                    )
                
                userinfo = userinfo_response.json()
            
            # Update the session
            await self.session_service.update_session(session_id, {
                "is_logged_in": True,
                "web_id": userinfo.get("webid"),
                "tokens": tokens,
                "userinfo": userinfo,
            })
            
            return {
                "success": True,
                "web_id": userinfo.get("webid"),
                "session_id": session_id,
            }
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"Callback handling error: {str(e)}")
            raise ApiError(f"Callback handling failed: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
    
    async def logout(self, session_id: str) -> Dict[str, Any]:
        """
        Logout from the Solid identity provider
        
        Args:
            session_id: The session ID
            
        Returns:
            Dict: Success status and message
            
        Raises:
            ApiError: If logout fails
        """
        if not session_id:
            raise ApiError("Session ID is required", HTTPStatus.BAD_REQUEST)
        
        try:
            # Get the session
            session = await self.session_service.get_session(session_id)
            
            # Delete the session
            await self.session_service.delete_session(session_id)
            
            return {
                "success": True,
                "message": "Logged out successfully",
            }
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            raise ApiError(f"Logout failed: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get current session info
        
        Args:
            session_id: The session ID
            
        Returns:
            Dict: Session information
            
        Raises:
            ApiError: If session retrieval fails
        """
        if not session_id:
            raise ApiError("Session ID is required", HTTPStatus.BAD_REQUEST)
        
        try:
            # Get the session
            session = await self.session_service.get_session(session_id)
            
            return {
                "is_logged_in": session.is_logged_in,
                "web_id": session.web_id,
                "session_id": session_id,
            }
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"Get session error: {str(e)}")
            raise ApiError(f"Get session failed: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR) 