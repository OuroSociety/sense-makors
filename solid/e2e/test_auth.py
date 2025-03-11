import os
import pytest
import requests
from http import HTTPStatus

# Base URL for the API
API_URL = os.getenv("API_URL", "http://localhost:3000")

# Test OIDC issuer (Inrupt's test identity provider)
TEST_OIDC_ISSUER = "https://login.inrupt.com/"

class TestAuthAPI:
    """E2E tests for the authentication API"""
    
    # Test session ID
    session_id = None
    
    # Test login URL
    login_url = None
    
    def test_login(self):
        """Test login endpoint"""
        try:
            response = requests.post(
                f"{API_URL}/api/auth/login",
                json={"oidc_issuer": TEST_OIDC_ISSUER},
            )
            
            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert "session_id" in data
            assert "login_url" in data
            
            # Save session ID and login URL for later tests
            TestAuthAPI.session_id = data["session_id"]
            TestAuthAPI.login_url = data["login_url"]
            
            # Verify login URL format
            assert TEST_OIDC_ISSUER in TestAuthAPI.login_url
            assert "client_id=" in TestAuthAPI.login_url
            assert "redirect_uri=" in TestAuthAPI.login_url
            assert "response_type=code" in TestAuthAPI.login_url
        except requests.exceptions.ConnectionError:
            pytest.skip("Server is not running, skipping test")
    
    def test_register(self):
        """Test register endpoint"""
        try:
            response = requests.post(
                f"{API_URL}/api/auth/register",
                json={"oidc_issuer": TEST_OIDC_ISSUER},
            )
            
            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert "registration_url" in data
            assert "message" in data
            
            # Verify registration URL format
            assert data["registration_url"] == f"{TEST_OIDC_ISSUER}/register"
        except requests.exceptions.ConnectionError:
            pytest.skip("Server is not running, skipping test")
    
    # Note: We can't fully test the callback and authenticated endpoints in an automated test
    # because they require user interaction with the identity provider.
    # In a real-world scenario, you would use a mock identity provider or
    # integration tests with Playwright/Selenium for full E2E testing.
    
    def test_session_without_id(self):
        """Test session endpoint without session ID"""
        try:
            response = requests.get(f"{API_URL}/api/auth/session")
            assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        except requests.exceptions.ConnectionError:
            pytest.skip("Server is not running, skipping test")
    
    def test_session_with_invalid_id(self):
        """Test session endpoint with invalid session ID"""
        try:
            response = requests.get(
                f"{API_URL}/api/auth/session",
                params={"session_id": "invalid-session-id"},
            )
            assert response.status_code == HTTPStatus.BAD_REQUEST
        except requests.exceptions.ConnectionError:
            pytest.skip("Server is not running, skipping test") 