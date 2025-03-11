import os
import json
import time
import uuid
import base64
import httpx
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, urlparse, parse_qs

from ..utils.exceptions import ApiError
from ..utils.logger import logger

class SolidOidcClient:
    """
    Solid OIDC authentication client
    
    This client provides methods for authenticating with Solid identity providers
    using the Solid-OIDC protocol, based on the solid-oidc-py repository.
    """
    
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        redirect_uri: str = None,
        issuer: str = None
    ):
        """
        Initialize the Solid OIDC client
        
        Args:
            client_id: Client ID for the OIDC provider
            client_secret: Client secret for the OIDC provider
            redirect_uri: Redirect URI for the OIDC flow
            issuer: OIDC issuer URL
        """
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("REDIRECT_URL", "http://localhost:3000/api/auth/callback")
        self.issuer = issuer
        self.client = httpx.AsyncClient(follow_redirects=True)
        self.config = None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def discover_configuration(self, issuer: str = None) -> Dict[str, Any]:
        """
        Discover the OIDC configuration for an issuer
        
        Args:
            issuer: OIDC issuer URL
            
        Returns:
            Dict: OIDC configuration
            
        Raises:
            ApiError: If discovery fails
        """
        issuer = issuer or self.issuer
        
        if not issuer:
            raise ApiError("No issuer provided")
        
        # Normalize the issuer URL
        if not issuer.endswith("/"):
            issuer += "/"
        
        # Check if we already have the configuration
        if self.config and self.issuer == issuer:
            return self.config
        
        # Discover the configuration
        try:
            # Try the standard OIDC discovery endpoint
            well_known_url = f"{issuer}.well-known/openid-configuration"
            response = await self.client.get(well_known_url)
            
            if response.status_code == 200:
                self.config = response.json()
                self.issuer = issuer
                return self.config
            
            # Try the alternative endpoint
            well_known_url = f"{issuer}.well-known/oauth-authorization-server"
            response = await self.client.get(well_known_url)
            
            if response.status_code == 200:
                self.config = response.json()
                self.issuer = issuer
                return self.config
            
            raise ApiError(f"Failed to discover OIDC configuration: {response.text}")
        except httpx.RequestError as e:
            logger.error(f"OIDC discovery error: {str(e)}")
            raise ApiError(f"OIDC discovery error: {str(e)}")
    
    async def register_client(self, issuer: str = None) -> Dict[str, Any]:
        """
        Register a client with an OIDC provider
        
        Args:
            issuer: OIDC issuer URL
            
        Returns:
            Dict: Client registration response
            
        Raises:
            ApiError: If registration fails
        """
        issuer = issuer or self.issuer
        
        if not issuer:
            raise ApiError("No issuer provided")
        
        # Discover the configuration
        config = await self.discover_configuration(issuer)
        
        # Check if the provider supports dynamic registration
        if "registration_endpoint" not in config:
            raise ApiError("OIDC provider does not support dynamic registration")
        
        # Prepare the registration request
        registration_data = {
            "client_name": os.getenv("CLIENT_NAME", "Solid Pod Server"),
            "redirect_uris": [self.redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "openid profile offline_access",
            "token_endpoint_auth_method": "client_secret_basic"
        }
        
        # Register the client
        try:
            response = await self.client.post(
                config["registration_endpoint"],
                json=registration_data
            )
            
            if response.status_code in [200, 201]:
                registration = response.json()
                
                # Update the client credentials
                self.client_id = registration["client_id"]
                self.client_secret = registration.get("client_secret")
                
                return registration
            else:
                raise ApiError(f"Client registration failed: {response.text}")
        except httpx.RequestError as e:
            logger.error(f"Client registration error: {str(e)}")
            raise ApiError(f"Client registration error: {str(e)}")
    
    async def create_authorization_url(
        self,
        issuer: str = None,
        scope: str = "openid profile offline_access",
        state: str = None,
        prompt: str = None
    ) -> Dict[str, str]:
        """
        Create an authorization URL for the OIDC flow
        
        Args:
            issuer: OIDC issuer URL
            scope: OAuth scope
            state: OAuth state parameter
            prompt: OAuth prompt parameter
            
        Returns:
            Dict: Authorization URL and state
            
        Raises:
            ApiError: If URL creation fails
        """
        issuer = issuer or self.issuer
        
        if not issuer:
            raise ApiError("No issuer provided")
        
        # Discover the configuration
        config = await self.discover_configuration(issuer)
        
        # Check if we have a client ID
        if not self.client_id:
            # Try to register a client
            registration = await self.register_client(issuer)
            self.client_id = registration["client_id"]
        
        # Generate a state if not provided
        if not state:
            state = str(uuid.uuid4())
        
        # Prepare the authorization parameters
        auth_params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": scope,
            "state": state
        }
        
        # Add prompt if provided
        if prompt:
            auth_params["prompt"] = prompt
        
        # Create the authorization URL
        auth_url = f"{config['authorization_endpoint']}?{urlencode(auth_params)}"
        
        return {
            "authorization_url": auth_url,
            "state": state
        }
    
    async def exchange_code_for_tokens(
        self,
        code: str,
        state: str = None,
        expected_state: str = None
    ) -> Dict[str, Any]:
        """
        Exchange an authorization code for tokens
        
        Args:
            code: Authorization code
            state: OAuth state parameter from the callback
            expected_state: Expected OAuth state parameter
            
        Returns:
            Dict: Token response
            
        Raises:
            ApiError: If token exchange fails
        """
        if not self.issuer:
            raise ApiError("No issuer configured")
        
        # Discover the configuration
        config = await self.discover_configuration()
        
        # Verify the state if provided
        if expected_state and state and expected_state != state:
            raise ApiError("State mismatch")
        
        # Prepare the token request
        token_params = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id
        }
        
        # Add client secret if available
        headers = {}
        if self.client_secret:
            # Use client authentication
            auth_str = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_str.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
            headers["Authorization"] = f"Basic {auth_b64}"
        
        # Exchange the code for tokens
        try:
            response = await self.client.post(
                config["token_endpoint"],
                data=token_params,
                headers=headers
            )
            
            if response.status_code == 200:
                tokens = response.json()
                
                # Extract the WebID from the ID token if available
                if "id_token" in tokens:
                    # Parse the ID token
                    id_token = tokens["id_token"]
                    parts = id_token.split(".")
                    
                    if len(parts) >= 2:
                        # Decode the payload
                        payload_b64 = parts[1]
                        # Add padding if needed
                        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                        payload_bytes = base64.urlsafe_b64decode(payload_b64)
                        payload = json.loads(payload_bytes)
                        
                        # Extract the WebID
                        webid = payload.get("webid") or payload.get("sub")
                        tokens["webid"] = webid
                
                return tokens
            else:
                raise ApiError(f"Token exchange failed: {response.text}")
        except httpx.RequestError as e:
            logger.error(f"Token exchange error: {str(e)}")
            raise ApiError(f"Token exchange error: {str(e)}")
    
    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access tokens using a refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict: Token response
            
        Raises:
            ApiError: If token refresh fails
        """
        if not self.issuer:
            raise ApiError("No issuer configured")
        
        # Discover the configuration
        config = await self.discover_configuration()
        
        # Prepare the token request
        token_params = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id
        }
        
        # Add client secret if available
        headers = {}
        if self.client_secret:
            # Use client authentication
            auth_str = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_str.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
            headers["Authorization"] = f"Basic {auth_b64}"
        
        # Refresh the tokens
        try:
            response = await self.client.post(
                config["token_endpoint"],
                data=token_params,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise ApiError(f"Token refresh failed: {response.text}")
        except httpx.RequestError as e:
            logger.error(f"Token refresh error: {str(e)}")
            raise ApiError(f"Token refresh error: {str(e)}")
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate an access token
        
        Args:
            token: Access token
            
        Returns:
            Dict: Token validation response
            
        Raises:
            ApiError: If token validation fails
        """
        if not self.issuer:
            raise ApiError("No issuer configured")
        
        # Discover the configuration
        config = await self.discover_configuration()
        
        # Check if the provider has an introspection endpoint
        if "introspection_endpoint" not in config:
            raise ApiError("OIDC provider does not support token introspection")
        
        # Prepare the introspection request
        introspection_params = {
            "token": token,
            "token_type_hint": "access_token"
        }
        
        # Add client credentials
        headers = {}
        if self.client_id and self.client_secret:
            # Use client authentication
            auth_str = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_str.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
            headers["Authorization"] = f"Basic {auth_b64}"
        
        # Validate the token
        try:
            response = await self.client.post(
                config["introspection_endpoint"],
                data=introspection_params,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise ApiError(f"Token validation failed: {response.text}")
        except httpx.RequestError as e:
            logger.error(f"Token validation error: {str(e)}")
            raise ApiError(f"Token validation error: {str(e)}")
    
    async def end_session(self, id_token: str = None) -> Optional[str]:
        """
        End the user's session with the OIDC provider
        
        Args:
            id_token: ID token
            
        Returns:
            Optional[str]: End session URL or None if not supported
            
        Raises:
            ApiError: If session termination fails
        """
        if not self.issuer:
            raise ApiError("No issuer configured")
        
        # Discover the configuration
        config = await self.discover_configuration()
        
        # Check if the provider has an end session endpoint
        if "end_session_endpoint" not in config:
            return None
        
        # Prepare the end session parameters
        end_session_params = {
            "client_id": self.client_id,
            "post_logout_redirect_uri": self.redirect_uri
        }
        
        # Add ID token if available
        if id_token:
            end_session_params["id_token_hint"] = id_token
        
        # Create the end session URL
        end_session_url = f"{config['end_session_endpoint']}?{urlencode(end_session_params)}"
        
        return end_session_url 