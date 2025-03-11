import os
import json
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, BinaryIO
import httpx
from urllib.parse import urlparse, urljoin

from ..utils.exceptions import ApiError
from ..utils.logger import logger

class SolidFileClient:
    """
    Client for file operations on Solid Pods
    
    This client provides methods for reading, writing, and managing files in Solid Pods,
    based on the solid-file-python repository.
    """
    
    def __init__(self, access_token: str = None):
        """
        Initialize the Solid file client
        
        Args:
            access_token: Optional access token for authentication
        """
        self.access_token = access_token
        self.client = httpx.AsyncClient(follow_redirects=True)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        headers: Dict[str, str] = None, 
        data: Any = None,
        params: Dict[str, str] = None,
        content: Any = None
    ) -> httpx.Response:
        """
        Make an HTTP request to a Solid server
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
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
        headers = headers or {}
        
        # Add authorization header if we have an access token
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
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
                raise ApiError(
                    f"Request failed: {response.text}",
                    response.status_code
                )
            
            return response
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise ApiError(f"Request error: {str(e)}")
    
    async def read_file(self, url: str) -> bytes:
        """
        Read a file from a Solid Pod
        
        Args:
            url: URL of the file
            
        Returns:
            bytes: File content
            
        Raises:
            ApiError: If the request fails
        """
        response = await self._make_request("GET", url)
        
        return response.content
    
    async def read_file_as_text(self, url: str, encoding: str = "utf-8") -> str:
        """
        Read a file from a Solid Pod as text
        
        Args:
            url: URL of the file
            encoding: Text encoding
            
        Returns:
            str: File content as text
            
        Raises:
            ApiError: If the request fails
        """
        content = await self.read_file(url)
        
        return content.decode(encoding)
    
    async def read_file_as_json(self, url: str) -> Dict[str, Any]:
        """
        Read a file from a Solid Pod as JSON
        
        Args:
            url: URL of the file
            
        Returns:
            Dict: Parsed JSON content
            
        Raises:
            ApiError: If the request fails or the content is not valid JSON
        """
        text = await self.read_file_as_text(url)
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise ApiError(f"JSON decode error: {str(e)}")
    
    async def write_file(
        self, 
        url: str, 
        content: Union[bytes, str, Dict[str, Any]], 
        content_type: str = None
    ) -> bool:
        """
        Write a file to a Solid Pod
        
        Args:
            url: URL of the file
            content: File content
            content_type: Content type of the file
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        # Determine the content type if not provided
        if not content_type:
            # Try to guess from the URL
            parsed_url = urlparse(url)
            path = parsed_url.path
            content_type, _ = mimetypes.guess_type(path)
            
            # Default to octet-stream if we can't determine the type
            if not content_type:
                content_type = "application/octet-stream"
        
        # Prepare the content
        if isinstance(content, dict):
            # Convert dict to JSON
            content = json.dumps(content).encode("utf-8")
            if not content_type:
                content_type = "application/json"
        elif isinstance(content, str):
            # Convert string to bytes
            content = content.encode("utf-8")
            if not content_type:
                content_type = "text/plain"
        
        # Prepare headers
        headers = {
            "Content-Type": content_type
        }
        
        # Write the file
        response = await self._make_request("PUT", url, headers=headers, content=content)
        
        return response.status_code in [200, 201, 204]
    
    async def delete_file(self, url: str) -> bool:
        """
        Delete a file from a Solid Pod
        
        Args:
            url: URL of the file
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        response = await self._make_request("DELETE", url)
        
        return response.status_code in [200, 202, 204]
    
    async def create_folder(self, url: str) -> bool:
        """
        Create a folder in a Solid Pod
        
        Args:
            url: URL of the folder
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        # Make sure the URL ends with a slash
        if not url.endswith("/"):
            url += "/"
        
        headers = {
            "Content-Type": "text/turtle",
            "Link": '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'
        }
        
        response = await self._make_request("PUT", url, headers=headers)
        
        return response.status_code in [200, 201, 204]
    
    async def list_folder(self, url: str) -> List[Dict[str, Any]]:
        """
        List the contents of a folder
        
        Args:
            url: URL of the folder
            
        Returns:
            List[Dict]: List of files and folders
            
        Raises:
            ApiError: If the request fails
        """
        # Make sure the URL ends with a slash
        if not url.endswith("/"):
            url += "/"
        
        headers = {
            "Accept": "text/turtle"
        }
        
        response = await self._make_request("GET", url, headers=headers)
        
        # Parse the response as Turtle
        try:
            import rdflib
            from rdflib import Graph, URIRef
            
            g = Graph()
            g.parse(data=response.text, format="turtle")
            
            # Extract the contained resources
            resources = []
            
            # Find all resources in the container
            for s, p, o in g.triples((None, rdflib.RDF.type, URIRef("http://www.w3.org/ns/ldp#Resource"))):
                # Get the resource URL
                resource_url = str(s)
                
                # Check if it's a container
                is_container = False
                for _, _, container_type in g.triples((s, rdflib.RDF.type, URIRef("http://www.w3.org/ns/ldp#Container"))):
                    is_container = True
                    break
                
                # Get the resource name
                name = resource_url.rstrip("/").split("/")[-1]
                
                # Get the last modified date if available
                last_modified = None
                for _, _, modified in g.triples((s, URIRef("http://purl.org/dc/terms/modified"), None)):
                    last_modified = str(modified)
                    break
                
                resources.append({
                    "url": resource_url,
                    "name": name,
                    "is_container": is_container,
                    "last_modified": last_modified
                })
            
            return resources
        except Exception as e:
            logger.error(f"Error parsing folder contents: {str(e)}")
            raise ApiError(f"Error parsing folder contents: {str(e)}")
    
    async def copy_file(self, source_url: str, target_url: str) -> bool:
        """
        Copy a file from one location to another
        
        Args:
            source_url: URL of the source file
            target_url: URL of the target file
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        # Read the source file
        content = await self.read_file(source_url)
        
        # Get the content type
        response = await self._make_request("HEAD", source_url)
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        
        # Write to the target file
        return await self.write_file(target_url, content, content_type)
    
    async def move_file(self, source_url: str, target_url: str) -> bool:
        """
        Move a file from one location to another
        
        Args:
            source_url: URL of the source file
            target_url: URL of the target file
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        # Copy the file
        success = await self.copy_file(source_url, target_url)
        
        if success:
            # Delete the source file
            return await self.delete_file(source_url)
        
        return False
    
    async def upload_file(self, local_path: Union[str, Path], url: str, content_type: str = None) -> bool:
        """
        Upload a local file to a Solid Pod
        
        Args:
            local_path: Path to the local file
            url: URL to upload to
            content_type: Content type of the file
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        # Convert string path to Path
        if isinstance(local_path, str):
            local_path = Path(local_path)
        
        # Check if the file exists
        if not local_path.exists():
            raise ApiError(f"File not found: {local_path}")
        
        # Read the file
        with open(local_path, "rb") as f:
            content = f.read()
        
        # Determine the content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(str(local_path))
            if not content_type:
                content_type = "application/octet-stream"
        
        # Upload the file
        return await self.write_file(url, content, content_type)
    
    async def download_file(self, url: str, local_path: Union[str, Path]) -> bool:
        """
        Download a file from a Solid Pod to a local path
        
        Args:
            url: URL of the file
            local_path: Path to save the file to
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        # Convert string path to Path
        if isinstance(local_path, str):
            local_path = Path(local_path)
        
        # Create the parent directory if it doesn't exist
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download the file
        content = await self.read_file(url)
        
        # Write to the local file
        with open(local_path, "wb") as f:
            f.write(content)
        
        return True 