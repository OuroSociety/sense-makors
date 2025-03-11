from fastapi import APIRouter, Depends, Query, Body, Path, HTTPException
from http import HTTPStatus
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from ..controllers.pod_controller import PodController
from ..middleware.auth_middleware import get_session
from ..utils.exceptions import ApiError

# Create router
pod_router = APIRouter()

# Create controller instance
pod_controller = PodController()

# Models for request and response
class PodInfoResponse(BaseModel):
    web_id: str = Field(..., description="Web ID")
    name: str = Field(..., description="Name")
    storage: Optional[str] = Field(None, description="Storage location")

class CreatePodRequest(BaseModel):
    name: str = Field(..., description="Pod name")
    description: Optional[str] = Field(None, description="Pod description")

class CreatePodResponse(BaseModel):
    success: bool = Field(..., description="Success status")
    pod_url: str = Field(..., description="Pod URL")
    name: str = Field(..., description="Pod name")
    description: Optional[str] = Field(None, description="Pod description")

class ResourceInfo(BaseModel):
    url: str = Field(..., description="Resource URL")
    name: str = Field(..., description="Resource name")
    is_container: Optional[bool] = Field(None, description="Whether the resource is a container")
    last_modified: Optional[str] = Field(None, description="Last modified date")
    error: Optional[str] = Field(None, description="Error message if any")

class ListResourcesResponse(BaseModel):
    container_url: str = Field(..., description="Container URL")
    resources: List[ResourceInfo] = Field(..., description="List of resources")

class CreateResourceRequest(BaseModel):
    container_url: str = Field(..., description="Container URL")
    name: str = Field(..., description="Resource name")
    is_container: bool = Field(False, description="Whether to create a container")
    data: Optional[Dict[str, Any]] = Field(None, description="Resource data")

class CreateResourceResponse(BaseModel):
    success: bool = Field(..., description="Success status")
    resource_url: str = Field(..., description="Resource URL")
    name: str = Field(..., description="Resource name")
    is_container: bool = Field(..., description="Whether the resource is a container")

class ResourceData(BaseModel):
    id: str = Field(..., description="Resource ID")
    description: Optional[str] = Field(None, description="Resource description")
    data: Optional[Dict[str, Any]] = Field(None, description="Resource data")

class GetResourceResponse(BaseModel):
    resource_url: str = Field(..., description="Resource URL")
    is_container: bool = Field(..., description="Whether the resource is a container")
    source_url: Optional[str] = Field(None, description="Source URL")
    contained_resources: Optional[List[str]] = Field(None, description="Contained resources")
    data: Optional[List[ResourceData]] = Field(None, description="Resource data")

class UpdateResourceRequest(BaseModel):
    resource_url: str = Field(..., description="Resource URL")
    data: Dict[str, Any] = Field(..., description="Resource data")

class UpdateResourceResponse(BaseModel):
    success: bool = Field(..., description="Success status")
    resource_url: str = Field(..., description="Resource URL")
    data: Dict[str, Any] = Field(..., description="Resource data")

class DeleteResourceResponse(BaseModel):
    success: bool = Field(..., description="Success status")
    resource_url: str = Field(..., description="Resource URL")
    is_container: bool = Field(..., description="Whether the resource was a container")

# Routes
@pod_router.get("/info", response_model=PodInfoResponse, status_code=HTTPStatus.OK)
async def get_pod_info(session=Depends(get_session)):
    """
    Get information about the user's pod
    """
    try:
        return await pod_controller.get_pod_info(session)
    except ApiError as e:
        raise e
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

@pod_router.post("/create", response_model=CreatePodResponse, status_code=HTTPStatus.CREATED)
async def create_pod(request: CreatePodRequest, session=Depends(get_session)):
    """
    Create a new pod
    """
    try:
        return await pod_controller.create_pod(session, request.name, request.description)
    except ApiError as e:
        raise e
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

@pod_router.get("/resources", response_model=ListResourcesResponse, status_code=HTTPStatus.OK)
async def list_resources(
    container_url: str = Query(..., description="Container URL"),
    session=Depends(get_session)
):
    """
    List resources in a pod
    """
    try:
        return await pod_controller.list_resources(session, container_url)
    except ApiError as e:
        raise e
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

@pod_router.post("/resources", response_model=CreateResourceResponse, status_code=HTTPStatus.CREATED)
async def create_resource(request: CreateResourceRequest, session=Depends(get_session)):
    """
    Create a new resource in the pod
    """
    try:
        return await pod_controller.create_resource(
            session, 
            request.container_url, 
            request.name, 
            request.is_container, 
            request.data
        )
    except ApiError as e:
        raise e
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

@pod_router.get("/resources/{id}", response_model=GetResourceResponse, status_code=HTTPStatus.OK)
async def get_resource(
    id: str = Path(..., description="Resource ID"),
    resource_url: str = Query(..., description="Resource URL"),
    session=Depends(get_session)
):
    """
    Get a specific resource from the pod
    """
    try:
        return await pod_controller.get_resource(session, id, resource_url)
    except ApiError as e:
        raise e
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

@pod_router.put("/resources/{id}", response_model=UpdateResourceResponse, status_code=HTTPStatus.OK)
async def update_resource(
    id: str = Path(..., description="Resource ID"),
    request: UpdateResourceRequest = Body(...),
    session=Depends(get_session)
):
    """
    Update a specific resource in the pod
    """
    try:
        return await pod_controller.update_resource(session, id, request.resource_url, request.data)
    except ApiError as e:
        raise e
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

@pod_router.delete("/resources/{id}", response_model=DeleteResourceResponse, status_code=HTTPStatus.OK)
async def delete_resource(
    id: str = Path(..., description="Resource ID"),
    resource_url: str = Query(..., description="Resource URL"),
    session=Depends(get_session)
):
    """
    Delete a specific resource from the pod
    """
    try:
        return await pod_controller.delete_resource(session, id, resource_url)
    except ApiError as e:
        raise e
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR) 