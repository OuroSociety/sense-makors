import os
import json
import time
import base64
import httpx
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

from ..utils.exceptions import ApiError
from ..utils.logger import logger

class ClientCredentialsClient:
    """
    Client credentials authentication client
    
    This client provides methods for authenticating with Solid servers using
    client credentials, based on the solid-client-credentials-py repository.
    """
    
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        token_endpoint: str = None
    ):
        """
        Initialize the client credentials client
        
        Args:
            client_id: Client ID
            client_secret: Client secret
            token_endpoint: Token endpoint URL
        """
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.token_endpoint = token_endpoint
        self.client = httpx.AsyncClient(follow_redirects=True)
        self.access_token = None
        self.token_expiry = 0
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def get_token(self, force_refresh: bool = False) -> str:
        """
        Get an access token
        
        Args:
            force_refresh: Whether to force a token refresh
            
        Returns:
            str: Access token
            
        Raises:
            ApiError: If token acquisition fails
        """
        # Check if we have a valid token
        if not force_refresh and self.access_token and time.time() < self.token_expiry:
            return self.access_token
        
        # Check if we have the required credentials
        if not self.client_id or not self.client_secret:
            raise ApiError("Client ID and secret are required")
        
        if not self.token_endpoint:
            raise ApiError("Token endpoint is required")
        
        # Prepare the token request
        token_params = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "openid"
        }
        
        # Get the token
        try:
            response = await self.client.post(
                self.token_endpoint,
                data=token_params
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Store the token
                self.access_token = token_data["access_token"]
                
                # Calculate the expiry time
                expires_in = token_data.get("expires_in", 3600)
                self.token_expiry = time.time() + expires_in - 60  # Refresh 60 seconds before expiry
                
                return self.access_token
            else:
                raise ApiError(f"Token acquisition failed: {response.text}")
        except httpx.RequestError as e:
            logger.error(f"Token acquisition error: {str(e)}")
            raise ApiError(f"Token acquisition error: {str(e)}")
    
    async def make_authenticated_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        data: Any = None,
        params: Dict[str, str] = None,
        content: Any = None
    ) -> httpx.Response:
        """
        Make an authenticated request
        
        Args:
            method: HTTP method
            url: URL to request
            headers: Optional HTTP headers
            data: Optional data for POST/PUT requests
            params: Optional query parameters
            content: Optional content for the request body
            
        Returns:
            Response: HTTP response
            
        Raises:
            ApiError: If the request fails
        """
        # Get an access token
        token = await self.get_token()
        
        # Prepare the headers
        headers = headers or {}
        headers["Authorization"] = f"Bearer {token}"
        
        # Make the request
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                params=params,
                content=content,
                timeout=30.0
            )
            
            # Check for error status codes
            if response.status_code >= 400:
                # If unauthorized, try refreshing the token
                if response.status_code == 401:
                    token = await self.get_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {token}"
                    
                    # Retry the request
                    response = await self.client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        data=data,
                        params=params,
                        content=content,
                        timeout=30.0
                    )
                    
                    if response.status_code >= 400:
                        raise ApiError(
                            f"Request failed after token refresh: {response.text}",
                            response.status_code
                        )
                else:
                    raise ApiError(
                        f"Request failed: {response.text}",
                        response.status_code
                    )
            
            return response
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise ApiError(f"Request error: {str(e)}")
    
    @staticmethod
    async def register_client(
        registration_endpoint: str,
        client_name: str = None,
        redirect_uris: List[str] = None
    ) -> Dict[str, Any]:
        """
        Register a client with a Solid server
        
        Args:
            registration_endpoint: Client registration endpoint
            client_name: Client name
            redirect_uris: Redirect URIs
            
        Returns:
            Dict: Client registration response
            
        Raises:
            ApiError: If registration fails
        """
        # Prepare the registration request
        registration_data = {
            "client_name": client_name or os.getenv("CLIENT_NAME", "Solid Pod Server"),
            "redirect_uris": redirect_uris or [os.getenv("REDIRECT_URL", "http://localhost:3000/api/auth/callback")],
            "grant_types": ["client_credentials"],
            "token_endpoint_auth_method": "client_secret_basic"
        }
        
        # Register the client
        client = httpx.AsyncClient()
        
        try:
            response = await client.post(
                registration_endpoint,
                json=registration_data
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                raise ApiError(f"Client registration failed: {response.text}")
        except httpx.RequestError as e:
            logger.error(f"Client registration error: {str(e)}")
            raise ApiError(f"Client registration error: {str(e)}")
        finally:
            await client.aclose() 