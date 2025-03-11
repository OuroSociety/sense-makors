from fastapi import APIRouter, Depends, Query, Body, HTTPException
from fastapi.security import OAuth2PasswordBearer
from http import HTTPStatus
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from ..controllers.auth_controller import AuthController
from ..utils.exceptions import ApiError

# Create router
auth_router = APIRouter()

# Create controller instance
auth_controller = AuthController()

# Models for request and response
class LoginRequest(BaseModel):
    oidc_issuer: str = Field(..., description="OIDC issuer URL")

class LoginResponse(BaseModel):
    session_id: str = Field(..., description="Session ID")
    login_url: str = Field(..., description="Login URL")

class RegisterRequest(BaseModel):
    oidc_issuer: str = Field(..., description="OIDC issuer URL")

class RegisterResponse(BaseModel):
    registration_url: str = Field(..., description="Registration URL")
    message: str = Field(..., description="Information message")

class LogoutRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")

class LogoutResponse(BaseModel):
    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Information message")

class SessionResponse(BaseModel):
    is_logged_in: bool = Field(..., description="Login status")
    web_id: Optional[str] = Field(None, description="Web ID")
    session_id: str = Field(..., description="Session ID")

class CallbackResponse(BaseModel):
    success: bool = Field(..., description="Success status")
    web_id: Optional[str] = Field(None, description="Web ID")
    session_id: str = Field(..., description="Session ID")

# Routes
@auth_router.post("/login", response_model=LoginResponse, status_code=HTTPStatus.OK)
async def login(request: LoginRequest):
    """
    Login to a Solid identity provider
    """
    try:
        return await auth_controller.login(request.oidc_issuer)
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

@auth_router.post("/register", response_model=RegisterResponse, status_code=HTTPStatus.OK)
async def register(request: RegisterRequest):
    """
    Register with a Solid identity provider
    """
    try:
        return await auth_controller.register(request.oidc_issuer)
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

@auth_router.get("/callback", response_model=CallbackResponse, status_code=HTTPStatus.OK)
async def handle_callback(
    session_id: str = Query(..., description="Session ID"),
    code: Optional[str] = Query(None, description="Authorization code"),
    state: Optional[str] = Query(None, description="State parameter"),
):
    """
    Handle callback from Solid identity provider
    """
    try:
        return await auth_controller.handle_callback(session_id, code, state)
    except ApiError as e:
        raise e
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

@auth_router.post("/logout", response_model=LogoutResponse, status_code=HTTPStatus.OK)
async def logout(request: LogoutRequest):
    """
    Logout from the Solid identity provider
    """
    try:
        return await auth_controller.logout(request.session_id)
    except ApiError as e:
        raise e
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

@auth_router.get("/session", response_model=SessionResponse, status_code=HTTPStatus.OK)
async def get_session(session_id: str = Query(..., description="Session ID")):
    """
    Get current session info
    """
    try:
        return await auth_controller.get_session(session_id)
    except ApiError as e:
        raise e
    except Exception as e:
        raise ApiError(str(e), HTTPStatus.INTERNAL_SERVER_ERROR) 