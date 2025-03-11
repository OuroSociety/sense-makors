import os
import json
from typing import Dict, Any, Optional, List
from http import HTTPStatus
import httpx
import rdflib
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import FOAF, RDF, DCTERMS

from ..middleware.auth_middleware import Session
from ..utils.exceptions import ApiError
from ..utils.logger import logger

class PodController:
    """Controller for Pod management operations"""
    
    async def get_pod_info(self, session: Session) -> Dict[str, Any]:
        """
        Get information about the user's pod
        
        Args:
            session: The user's session
            
        Returns:
            Dict: Pod information
            
        Raises:
            ApiError: If pod info retrieval fails
        """
        if not session or not session.is_logged_in or not session.web_id:
            raise ApiError("Not authenticated", HTTPStatus.UNAUTHORIZED)
        
        try:
            web_id = session.web_id
            
            # Fetch the WebID profile
            response = await session.fetch(web_id)
            
            if response.status_code != HTTPStatus.OK:
                raise ApiError(f"Failed to fetch profile: {response.text}", HTTPStatus.NOT_FOUND)
            
            # Parse the profile as RDF
            g = Graph()
            g.parse(data=response.text, format="turtle")
            
            # Extract profile information
            name = None
            storage = None
            
            for s, p, o in g.triples((URIRef(web_id), FOAF.name, None)):
                name = str(o)
                break
            
            for s, p, o in g.triples((URIRef(web_id), URIRef("http://www.w3.org/ns/pim/space#storage"), None)):
                storage = str(o)
                break
            
            return {
                "web_id": web_id,
                "name": name or "Unknown",
                "storage": storage,
            }
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"Error getting pod info: {str(e)}")
            raise ApiError(f"Failed to get pod info: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
    
    async def create_pod(
        self, session: Session, name: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new pod
        
        Args:
            session: The user's session
            name: Pod name
            description: Pod description
            
        Returns:
            Dict: Created pod information
            
        Raises:
            ApiError: If pod creation fails
        """
        if not session or not session.is_logged_in:
            raise ApiError("Not authenticated", HTTPStatus.UNAUTHORIZED)
        
        if not name:
            raise ApiError("Pod name is required", HTTPStatus.BAD_REQUEST)
        
        try:
            # This is a simplified approach - in a real app, you would need to
            # interact with the Solid server's pod management API, which varies
            # by implementation
            
            # For this example, we'll create a container in the user's storage
            web_id = session.web_id
            
            if not web_id:
                raise ApiError("WebID not found", HTTPStatus.BAD_REQUEST)
            
            # Fetch the WebID profile to get the storage location
            pod_info = await self.get_pod_info(session)
            storage = pod_info.get("storage")
            
            if not storage:
                raise ApiError("Storage location not found in profile", HTTPStatus.NOT_FOUND)
            
            # Create a container for the pod
            pod_url = f"{storage}{name}/"
            
            # Make sure the URL ends with a slash for containers
            if not pod_url.endswith("/"):
                pod_url += "/"
            
            # Create the container
            response = await session.fetch(
                pod_url,
                {
                    "method": "PUT",
                    "headers": {
                        "Content-Type": "text/turtle",
                        "Link": '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"',
                    },
                },
            )
            
            if response.status_code not in [HTTPStatus.CREATED, HTTPStatus.OK]:
                if response.status_code == HTTPStatus.CONFLICT:
                    raise ApiError("A pod with this name already exists", HTTPStatus.CONFLICT)
                else:
                    raise ApiError(f"Failed to create pod: {response.text}", HTTPStatus.INTERNAL_SERVER_ERROR)
            
            # Create a README file with the description
            if description:
                # Create a graph for the README
                g = Graph()
                readme_uri = URIRef(f"{pod_url}README")
                g.add((readme_uri, DCTERMS.description, Literal(description)))
                
                # Serialize the graph to Turtle
                readme_turtle = g.serialize(format="turtle")
                
                # Save the README
                response = await session.fetch(
                    f"{pod_url}README",
                    {
                        "method": "PUT",
                        "headers": {
                            "Content-Type": "text/turtle",
                        },
                        "content": readme_turtle,
                    },
                )
                
                if response.status_code not in [HTTPStatus.CREATED, HTTPStatus.OK]:
                    logger.warning(f"Failed to create README: {response.text}")
            
            return {
                "success": True,
                "pod_url": pod_url,
                "name": name,
                "description": description,
            }
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"Error creating pod: {str(e)}")
            raise ApiError(f"Failed to create pod: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
    
    async def list_resources(self, session: Session, container_url: str) -> Dict[str, Any]:
        """
        List resources in a pod
        
        Args:
            session: The user's session
            container_url: Container URL
            
        Returns:
            Dict: List of resources
            
        Raises:
            ApiError: If resource listing fails
        """
        if not session or not session.is_logged_in:
            raise ApiError("Not authenticated", HTTPStatus.UNAUTHORIZED)
        
        if not container_url:
            raise ApiError("Container URL is required", HTTPStatus.BAD_REQUEST)
        
        try:
            # Make sure the URL ends with a slash for containers
            if not container_url.endswith("/"):
                container_url += "/"
            
            # Fetch the container
            response = await session.fetch(container_url)
            
            if response.status_code != HTTPStatus.OK:
                raise ApiError(f"Failed to fetch container: {response.text}", HTTPStatus.NOT_FOUND)
            
            # Parse the container as RDF
            g = Graph()
            g.parse(data=response.text, format="turtle")
            
            # Get all contained resources
            contained_resources = []
            
            for s, p, o in g.triples((None, RDF.type, URIRef("http://www.w3.org/ns/ldp#Resource"))):
                contained_resources.append(str(s))
            
            # Get information about each resource
            resources_info = []
            
            for resource_url in contained_resources:
                try:
                    # Fetch resource info
                    head_response = await session.fetch(
                        resource_url,
                        {
                            "method": "HEAD",
                        },
                    )
                    
                    # Check if it's a container
                    is_container = False
                    last_modified = None
                    
                    if "Link" in head_response.headers:
                        link_header = head_response.headers["Link"]
                        is_container = 'rel="type"' in link_header and "Container" in link_header
                    
                    if "Last-Modified" in head_response.headers:
                        last_modified = head_response.headers["Last-Modified"]
                    
                    resources_info.append({
                        "url": resource_url,
                        "name": resource_url.split("/")[-1],
                        "is_container": is_container,
                        "last_modified": last_modified,
                    })
                except Exception as e:
                    logger.error(f"Error getting info for resource {resource_url}: {str(e)}")
                    resources_info.append({
                        "url": resource_url,
                        "name": resource_url.split("/")[-1],
                        "error": "Failed to fetch resource info",
                    })
            
            return {
                "container_url": container_url,
                "resources": resources_info,
            }
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"Error listing resources: {str(e)}")
            raise ApiError(f"Failed to list resources: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
    
    async def create_resource(
        self,
        session: Session,
        container_url: str,
        name: str,
        is_container: bool = False,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new resource in the pod
        
        Args:
            session: The user's session
            container_url: Container URL
            name: Resource name
            is_container: Whether to create a container
            data: Resource data
            
        Returns:
            Dict: Created resource information
            
        Raises:
            ApiError: If resource creation fails
        """
        if not session or not session.is_logged_in:
            raise ApiError("Not authenticated", HTTPStatus.UNAUTHORIZED)
        
        if not container_url or not name:
            raise ApiError("Container URL and resource name are required", HTTPStatus.BAD_REQUEST)
        
        try:
            # Make sure the container URL ends with a slash
            if not container_url.endswith("/"):
                container_url += "/"
            
            # Create the resource URL
            resource_url = f"{container_url}{name}"
            
            # Add a trailing slash for containers
            if is_container and not resource_url.endswith("/"):
                resource_url += "/"
            
            if is_container:
                # Create a container
                response = await session.fetch(
                    resource_url,
                    {
                        "method": "PUT",
                        "headers": {
                            "Content-Type": "text/turtle",
                            "Link": '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"',
                        },
                    },
                )
            else:
                # Create a dataset with the provided data
                g = Graph()
                resource_uri = URIRef(resource_url)
                
                if data:
                    # Add data as properties
                    g.add((resource_uri, RDF.type, URIRef("http://www.w3.org/ns/ldp#Resource")))
                    g.add((resource_uri, DCTERMS.description, Literal(json.dumps(data))))
                
                # Serialize the graph to Turtle
                turtle_data = g.serialize(format="turtle")
                
                # Create the resource
                response = await session.fetch(
                    resource_url,
                    {
                        "method": "PUT",
                        "headers": {
                            "Content-Type": "text/turtle",
                        },
                        "content": turtle_data,
                    },
                )
            
            if response.status_code not in [HTTPStatus.CREATED, HTTPStatus.OK]:
                if response.status_code == HTTPStatus.CONFLICT:
                    raise ApiError("A resource with this name already exists", HTTPStatus.CONFLICT)
                else:
                    raise ApiError(f"Failed to create resource: {response.text}", HTTPStatus.INTERNAL_SERVER_ERROR)
            
            return {
                "success": True,
                "resource_url": resource_url,
                "name": name,
                "is_container": is_container,
            }
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"Error creating resource: {str(e)}")
            raise ApiError(f"Failed to create resource: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
    
    async def get_resource(
        self, session: Session, id: str, resource_url: str
    ) -> Dict[str, Any]:
        """
        Get a specific resource from the pod
        
        Args:
            session: The user's session
            id: Resource ID
            resource_url: Resource URL
            
        Returns:
            Dict: Resource information
            
        Raises:
            ApiError: If resource retrieval fails
        """
        if not session or not session.is_logged_in:
            raise ApiError("Not authenticated", HTTPStatus.UNAUTHORIZED)
        
        if not resource_url:
            raise ApiError("Resource URL is required", HTTPStatus.BAD_REQUEST)
        
        try:
            # Get resource info to determine if it's a container
            head_response = await session.fetch(
                resource_url,
                {
                    "method": "HEAD",
                },
            )
            
            # Check if it's a container
            is_container = False
            
            if "Link" in head_response.headers:
                link_header = head_response.headers["Link"]
                is_container = 'rel="type"' in link_header and "Container" in link_header
            
            if is_container:
                # If it's a container, list its contents
                container_info = await self.list_resources(session, resource_url)
                
                return {
                    "resource_url": resource_url,
                    "is_container": True,
                    "contained_resources": [r["url"] for r in container_info["resources"]],
                }
            else:
                # If it's a file, get its contents
                response = await session.fetch(resource_url)
                
                if response.status_code != HTTPStatus.OK:
                    raise ApiError(f"Failed to fetch resource: {response.text}", HTTPStatus.NOT_FOUND)
                
                # Parse the resource as RDF
                g = Graph()
                g.parse(data=response.text, format="turtle")
                
                # Extract data from the graph
                data = []
                
                for s, p, o in g.triples((None, DCTERMS.description, None)):
                    description = str(o)
                    
                    # Try to parse JSON if the description is JSON
                    try:
                        parsed_data = json.loads(description)
                    except json.JSONDecodeError:
                        parsed_data = None
                    
                    data.append({
                        "id": str(s),
                        "description": description,
                        "data": parsed_data,
                    })
                
                return {
                    "resource_url": resource_url,
                    "is_container": False,
                    "source_url": resource_url,
                    "data": data,
                }
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"Error getting resource: {str(e)}")
            raise ApiError(f"Failed to get resource: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
    
    async def update_resource(
        self, session: Session, id: str, resource_url: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a specific resource in the pod
        
        Args:
            session: The user's session
            id: Resource ID
            resource_url: Resource URL
            data: Resource data
            
        Returns:
            Dict: Updated resource information
            
        Raises:
            ApiError: If resource update fails
        """
        if not session or not session.is_logged_in:
            raise ApiError("Not authenticated", HTTPStatus.UNAUTHORIZED)
        
        if not resource_url:
            raise ApiError("Resource URL is required", HTTPStatus.BAD_REQUEST)
        
        try:
            # Get the existing resource
            response = await session.fetch(resource_url)
            
            if response.status_code != HTTPStatus.OK:
                raise ApiError(f"Failed to fetch resource: {response.text}", HTTPStatus.NOT_FOUND)
            
            # Parse the resource as RDF
            g = Graph()
            g.parse(data=response.text, format="turtle")
            
            # Update or create a thing with the new data
            resource_uri = URIRef(resource_url)
            
            # Remove existing description
            g.remove((resource_uri, DCTERMS.description, None))
            
            # Add new description
            g.add((resource_uri, DCTERMS.description, Literal(json.dumps(data))))
            
            # Serialize the graph to Turtle
            turtle_data = g.serialize(format="turtle")
            
            # Save the updated resource
            update_response = await session.fetch(
                resource_url,
                {
                    "method": "PUT",
                    "headers": {
                        "Content-Type": "text/turtle",
                    },
                    "content": turtle_data,
                },
            )
            
            if update_response.status_code not in [HTTPStatus.OK, HTTPStatus.CREATED]:
                raise ApiError(f"Failed to update resource: {update_response.text}", HTTPStatus.INTERNAL_SERVER_ERROR)
            
            return {
                "success": True,
                "resource_url": resource_url,
                "data": data,
            }
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"Error updating resource: {str(e)}")
            raise ApiError(f"Failed to update resource: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
    
    async def delete_resource(
        self, session: Session, id: str, resource_url: str
    ) -> Dict[str, Any]:
        """
        Delete a specific resource from the pod
        
        Args:
            session: The user's session
            id: Resource ID
            resource_url: Resource URL
            
        Returns:
            Dict: Deletion status
            
        Raises:
            ApiError: If resource deletion fails
        """
        if not session or not session.is_logged_in:
            raise ApiError("Not authenticated", HTTPStatus.UNAUTHORIZED)
        
        if not resource_url:
            raise ApiError("Resource URL is required", HTTPStatus.BAD_REQUEST)
        
        try:
            # Get resource info to determine if it's a container
            head_response = await session.fetch(
                resource_url,
                {
                    "method": "HEAD",
                },
            )
            
            # Check if it's a container
            is_container = False
            
            if "Link" in head_response.headers:
                link_header = head_response.headers["Link"]
                is_container = 'rel="type"' in link_header and "Container" in link_header
            
            # Delete the resource
            response = await session.fetch(
                resource_url,
                {
                    "method": "DELETE",
                },
            )
            
            if response.status_code not in [HTTPStatus.OK, HTTPStatus.NO_CONTENT]:
                raise ApiError(f"Failed to delete resource: {response.text}", HTTPStatus.INTERNAL_SERVER_ERROR)
            
            return {
                "success": True,
                "resource_url": resource_url,
                "is_container": is_container,
            }
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"Error deleting resource: {str(e)}")
            raise ApiError(f"Failed to delete resource: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR) 