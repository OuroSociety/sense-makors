from fastapi import HTTPException
from http import HTTPStatus

class ApiError(HTTPException):
    """Custom API exception with status code and detail message"""
    
    def __init__(self, detail: str, status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail) 