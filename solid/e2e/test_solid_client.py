import os
import sys
import pytest
import requests
import json
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import the client modules
from src.client import SolidClient, SolidFileClient

# Base URL for the API
API_URL = os.getenv("API_URL", "http://localhost:3000")

class TestSolidClient:
    """E2E tests for the Solid client"""
    
    # Test WebID
    webid = None
    
    # Test access token
    access_token = None
    
    @classmethod
    def setup_class(cls):
        """Set up the test class"""
        # Check if we have a WebID and access token in the environment
        cls.webid = os.getenv("TEST_WEBID")
        cls.access_token = os.getenv("TEST_ACCESS_TOKEN")
        
        # Check if we have a tokens file
        tokens_file = Path("solid_tokens.json")
        if tokens_file.exists() and not cls.access_token:
            try:
                with open(tokens_file, "r") as f:
                    tokens = json.load(f)
                    cls.access_token = tokens.get("access_token")
                    cls.webid = tokens.get("webid")
            except Exception as e:
                print(f"Error loading tokens file: {e}")
    
    def test_health_check(self):
        """Test the health check endpoint"""
        response = requests.get(f"{API_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    @pytest.mark.skipif(not os.getenv("TEST_WEBID"), reason="TEST_WEBID not set")
    def test_get_webid_profile(self):
        """Test getting a WebID profile"""
        # Create a client
        client = SolidClient()
        
        # Get the profile
        profile = pytest.asyncio.run(client.get_webid_profile(self.webid))
        
        # Check the profile
        assert profile["webid"] == self.webid
        assert "name" in profile
        assert "storage" in profile
        
        # Close the client
        pytest.asyncio.run(client.close())
    
    @pytest.mark.skipif(not os.getenv("TEST_ACCESS_TOKEN"), reason="TEST_ACCESS_TOKEN not set")
    def test_file_operations(self):
        """Test file operations"""
        # Create a file client
        file_client = SolidFileClient(access_token=self.access_token)
        
        # Create a test folder
        storage = os.getenv("TEST_STORAGE")
        if not storage:
            pytest.skip("TEST_STORAGE not set")
        
        test_folder_url = f"{storage}test/"
        test_file_url = f"{test_folder_url}test.txt"
        test_content = "Hello, Solid!"
        
        try:
            # Create the folder
            success = pytest.asyncio.run(file_client.create_folder(test_folder_url))
            assert success
            
            # Write a file
            success = pytest.asyncio.run(file_client.write_file(
                test_file_url,
                test_content,
                "text/plain"
            ))
            assert success
            
            # Read the file
            content = pytest.asyncio.run(file_client.read_file_as_text(test_file_url))
            assert content == test_content
            
            # List the folder
            resources = pytest.asyncio.run(file_client.list_folder(test_folder_url))
            assert len(resources) > 0
            assert any(r["url"] == test_file_url for r in resources)
            
            # Delete the file
            success = pytest.asyncio.run(file_client.delete_file(test_file_url))
            assert success
            
            # Delete the folder
            success = pytest.asyncio.run(file_client.delete_file(test_folder_url))
            assert success
        finally:
            # Close the client
            pytest.asyncio.run(file_client.close())
    
    @pytest.mark.skipif(not os.getenv("TEST_ACCESS_TOKEN"), reason="TEST_ACCESS_TOKEN not set")
    def test_container_operations(self):
        """Test container operations"""
        # Create a client
        client = SolidClient(access_token=self.access_token)
        
        # Create a test container
        storage = os.getenv("TEST_STORAGE")
        if not storage:
            pytest.skip("TEST_STORAGE not set")
        
        test_container_url = f"{storage}test-container/"
        
        try:
            # Create the container
            success = pytest.asyncio.run(client.create_container(test_container_url))
            assert success
            
            # Get the container contents
            resources = pytest.asyncio.run(client.get_container_contents(test_container_url))
            assert isinstance(resources, list)
            
            # Delete the container
            success = pytest.asyncio.run(client.delete_resource(test_container_url))
            assert success
        finally:
            # Close the client
            pytest.asyncio.run(client.close()) 