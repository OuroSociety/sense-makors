import os
import json
import httpx
import logging
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urlparse, urljoin
import rdflib
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import FOAF, RDF, DCTERMS

from ..utils.exceptions import ApiError
from ..utils.logger import logger

class SolidClient:
    """
    Client for interacting with Solid Pods
    
    This client provides methods for reading and writing data to Solid Pods,
    based on the WebID-TLS specification and inspired by solid-file-python,
    solid-client-credentials-py, and solid-oidc-py.
    """
    
    def __init__(self, session_id: str = None, access_token: str = None):
        """
        Initialize the Solid client
        
        Args:
            session_id: Optional session ID
            access_token: Optional access token for authentication
        """
        self.session_id = session_id
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
    
    async def read_resource(self, url: str, accept: str = "text/turtle") -> Graph:
        """
        Read a resource from a Solid Pod
        
        Args:
            url: URL of the resource
            accept: Accept header for content negotiation
            
        Returns:
            Graph: RDF graph containing the resource data
            
        Raises:
            ApiError: If the request fails
        """
        headers = {
            "Accept": accept
        }
        
        response = await self._make_request("GET", url, headers=headers)
        
        # Parse the response as RDF
        g = Graph()
        
        try:
            content_type = response.headers.get("Content-Type", "text/turtle").split(";")[0].strip()
            
            if content_type in ["text/turtle", "application/x-turtle"]:
                g.parse(data=response.text, format="turtle")
            elif content_type == "application/ld+json":
                g.parse(data=response.text, format="json-ld")
            elif content_type == "application/rdf+xml":
                g.parse(data=response.text, format="xml")
            else:
                # Default to Turtle
                g.parse(data=response.text, format="turtle")
            
            return g
        except Exception as e:
            logger.error(f"Error parsing RDF: {str(e)}")
            raise ApiError(f"Error parsing RDF: {str(e)}")
    
    async def write_resource(
        self, 
        url: str, 
        data: Union[Graph, str], 
        content_type: str = "text/turtle"
    ) -> bool:
        """
        Write a resource to a Solid Pod
        
        Args:
            url: URL of the resource
            data: RDF graph or serialized RDF data
            content_type: Content type of the data
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        headers = {
            "Content-Type": content_type
        }
        
        # Serialize the graph if it's an RDF graph
        if isinstance(data, Graph):
            if content_type == "text/turtle" or content_type == "application/x-turtle":
                content = data.serialize(format="turtle")
            elif content_type == "application/ld+json":
                content = data.serialize(format="json-ld")
            elif content_type == "application/rdf+xml":
                content = data.serialize(format="xml")
            else:
                content = data.serialize(format="turtle")
        else:
            content = data
        
        response = await self._make_request("PUT", url, headers=headers, content=content)
        
        return response.status_code in [200, 201, 204]
    
    async def create_container(self, url: str) -> bool:
        """
        Create a container in a Solid Pod
        
        Args:
            url: URL of the container
            
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
    
    async def delete_resource(self, url: str) -> bool:
        """
        Delete a resource from a Solid Pod
        
        Args:
            url: URL of the resource
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        response = await self._make_request("DELETE", url)
        
        return response.status_code in [200, 202, 204]
    
    async def get_container_contents(self, url: str) -> List[Dict[str, Any]]:
        """
        Get the contents of a container
        
        Args:
            url: URL of the container
            
        Returns:
            List[Dict]: List of resources in the container
            
        Raises:
            ApiError: If the request fails
        """
        # Make sure the URL ends with a slash
        if not url.endswith("/"):
            url += "/"
        
        # Read the container as RDF
        g = await self.read_resource(url)
        
        # Extract the contained resources
        resources = []
        
        # Find all resources in the container
        for s, p, o in g.triples((None, RDF.type, URIRef("http://www.w3.org/ns/ldp#Resource"))):
            # Get the resource URL
            resource_url = str(s)
            
            # Check if it's a container
            is_container = False
            for _, _, container_type in g.triples((s, RDF.type, URIRef("http://www.w3.org/ns/ldp#Container"))):
                is_container = True
                break
            
            # Get the resource name
            name = resource_url.rstrip("/").split("/")[-1]
            
            resources.append({
                "url": resource_url,
                "name": name,
                "is_container": is_container
            })
        
        return resources
    
    async def get_webid_profile(self, webid: str) -> Dict[str, Any]:
        """
        Get a WebID profile
        
        Args:
            webid: WebID URL
            
        Returns:
            Dict: Profile information
            
        Raises:
            ApiError: If the request fails
        """
        # Read the WebID profile
        g = await self.read_resource(webid)
        
        # Extract profile information
        profile = {
            "webid": webid,
            "name": None,
            "storage": None,
            "image": None,
            "friends": []
        }
        
        # Get the name
        for _, _, name in g.triples((URIRef(webid), FOAF.name, None)):
            profile["name"] = str(name)
            break
        
        # Get the storage location
        for _, _, storage in g.triples((URIRef(webid), URIRef("http://www.w3.org/ns/pim/space#storage"), None)):
            profile["storage"] = str(storage)
            break
        
        # Get the profile image
        for _, _, image in g.triples((URIRef(webid), FOAF.img, None)):
            profile["image"] = str(image)
            break
        
        # Get friends
        for _, _, friend in g.triples((URIRef(webid), FOAF.knows, None)):
            profile["friends"].append(str(friend))
        
        return profile
    
    async def update_webid_profile(self, webid: str, data: Dict[str, Any]) -> bool:
        """
        Update a WebID profile
        
        Args:
            webid: WebID URL
            data: Profile data to update
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        # Read the current profile
        g = await self.read_resource(webid)
        
        # Update the profile data
        webid_uri = URIRef(webid)
        
        # Update name
        if "name" in data:
            # Remove existing name
            g.remove((webid_uri, FOAF.name, None))
            # Add new name
            g.add((webid_uri, FOAF.name, Literal(data["name"])))
        
        # Update image
        if "image" in data:
            # Remove existing image
            g.remove((webid_uri, FOAF.img, None))
            # Add new image
            g.add((webid_uri, FOAF.img, URIRef(data["image"])))
        
        # Write the updated profile
        return await self.write_resource(webid, g)
    
    async def get_acl(self, resource_url: str) -> Optional[Graph]:
        """
        Get the ACL for a resource
        
        Args:
            resource_url: URL of the resource
            
        Returns:
            Optional[Graph]: ACL graph or None if not found
            
        Raises:
            ApiError: If the request fails
        """
        # Get the resource metadata
        headers = {
            "Accept": "text/turtle"
        }
        
        try:
            response = await self._make_request("HEAD", resource_url, headers=headers)
            
            # Check for Link header with ACL
            link_header = response.headers.get("Link", "")
            acl_url = None
            
            for link in link_header.split(","):
                if 'rel="acl"' in link:
                    # Extract the URL
                    acl_url = link.split(";")[0].strip("<>")
                    break
            
            if acl_url:
                # Read the ACL
                return await self.read_resource(acl_url)
            
            return None
        except ApiError:
            # ACL might not exist
            return None
    
    async def set_acl(self, resource_url: str, acl_data: Graph) -> bool:
        """
        Set the ACL for a resource
        
        Args:
            resource_url: URL of the resource
            acl_data: ACL graph
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the request fails
        """
        # Get the resource metadata
        headers = {
            "Accept": "text/turtle"
        }
        
        response = await self._make_request("HEAD", resource_url, headers=headers)
        
        # Check for Link header with ACL
        link_header = response.headers.get("Link", "")
        acl_url = None
        
        for link in link_header.split(","):
            if 'rel="acl"' in link:
                # Extract the URL
                acl_url = link.split(";")[0].strip("<>")
                break
        
        if not acl_url:
            # Try to construct the ACL URL
            parsed_url = urlparse(resource_url)
            path = parsed_url.path
            
            if path.endswith("/"):
                acl_url = f"{resource_url}.acl"
            else:
                acl_url = f"{resource_url}.acl"
        
        # Write the ACL
        return await self.write_resource(acl_url, acl_data)
    
    @staticmethod
    def create_acl_graph(resource_url: str, owner_webid: str) -> Graph:
        """
        Create an ACL graph for a resource
        
        Args:
            resource_url: URL of the resource
            owner_webid: WebID of the owner
            
        Returns:
            Graph: ACL graph
        """
        # Create a new graph
        g = Graph()
        
        # Add namespaces
        ACL = rdflib.Namespace("http://www.w3.org/ns/auth/acl#")
        g.bind("acl", ACL)
        g.bind("foaf", FOAF)
        
        # Create the ACL resource
        acl_url = f"{resource_url}.acl"
        
        # Create authorization for the owner
        auth = BNode()
        g.add((auth, RDF.type, ACL.Authorization))
        g.add((auth, ACL.accessTo, URIRef(resource_url)))
        g.add((auth, ACL.agent, URIRef(owner_webid)))
        g.add((auth, ACL.mode, ACL.Read))
        g.add((auth, ACL.mode, ACL.Write))
        g.add((auth, ACL.mode, ACL.Control))
        
        # Create authorization for public read access
        public_auth = BNode()
        g.add((public_auth, RDF.type, ACL.Authorization))
        g.add((public_auth, ACL.accessTo, URIRef(resource_url)))
        g.add((public_auth, ACL.agentClass, FOAF.Agent))
        g.add((public_auth, ACL.mode, ACL.Read))
        
        return g 