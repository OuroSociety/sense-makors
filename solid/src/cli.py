import os
import sys
import argparse
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from .client import SolidClient, SolidOidcClient, WebIdTlsAuth, SolidFileClient
from .utils.logger import logger

class SolidCli:
    """Command-line interface for the Solid client"""
    
    def __init__(self):
        """Initialize the CLI"""
        self.parser = self._create_parser()
        self.args = None
        self.client = None
        self.oidc_client = None
        self.file_client = None
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser"""
        parser = argparse.ArgumentParser(description="Solid Pod Client")
        
        # Global options
        parser.add_argument("--webid", help="WebID URL")
        parser.add_argument("--token", help="Access token")
        parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
        
        # Subparsers
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # Auth commands
        auth_parser = subparsers.add_parser("auth", help="Authentication commands")
        auth_subparsers = auth_parser.add_subparsers(dest="auth_command", help="Authentication command")
        
        # Login command
        login_parser = auth_subparsers.add_parser("login", help="Login to a Solid identity provider")
        login_parser.add_argument("--issuer", required=True, help="OIDC issuer URL")
        
        # Register command
        register_parser = auth_subparsers.add_parser("register", help="Register with a Solid identity provider")
        register_parser.add_argument("--issuer", required=True, help="OIDC issuer URL")
        
        # Generate certificate command
        cert_parser = auth_subparsers.add_parser("cert", help="Generate a WebID-TLS certificate")
        cert_parser.add_argument("--name", help="Common name for the certificate")
        cert_parser.add_argument("--output", "-o", help="Output directory for the certificate and key")
        
        # Pod commands
        pod_parser = subparsers.add_parser("pod", help="Pod management commands")
        pod_subparsers = pod_parser.add_subparsers(dest="pod_command", help="Pod command")
        
        # Info command
        info_parser = pod_subparsers.add_parser("info", help="Get information about a pod")
        
        # Create pod command
        create_pod_parser = pod_subparsers.add_parser("create", help="Create a new pod")
        create_pod_parser.add_argument("--name", required=True, help="Pod name")
        create_pod_parser.add_argument("--description", help="Pod description")
        
        # File commands
        file_parser = subparsers.add_parser("file", help="File operations")
        file_subparsers = file_parser.add_subparsers(dest="file_command", help="File command")
        
        # List command
        list_parser = file_subparsers.add_parser("list", help="List files in a container")
        list_parser.add_argument("url", help="Container URL")
        
        # Read command
        read_parser = file_subparsers.add_parser("read", help="Read a file")
        read_parser.add_argument("url", help="File URL")
        read_parser.add_argument("--output", "-o", help="Output file")
        
        # Write command
        write_parser = file_subparsers.add_parser("write", help="Write a file")
        write_parser.add_argument("url", help="File URL")
        write_parser.add_argument("--input", "-i", required=True, help="Input file or content")
        write_parser.add_argument("--content-type", help="Content type")
        
        # Delete command
        delete_parser = file_subparsers.add_parser("delete", help="Delete a file")
        delete_parser.add_argument("url", help="File URL")
        
        # Create folder command
        mkdir_parser = file_subparsers.add_parser("mkdir", help="Create a folder")
        mkdir_parser.add_argument("url", help="Folder URL")
        
        # Copy command
        copy_parser = file_subparsers.add_parser("copy", help="Copy a file")
        copy_parser.add_argument("source", help="Source URL")
        copy_parser.add_argument("target", help="Target URL")
        
        # Move command
        move_parser = file_subparsers.add_parser("move", help="Move a file")
        move_parser.add_argument("source", help="Source URL")
        move_parser.add_argument("target", help="Target URL")
        
        # Upload command
        upload_parser = file_subparsers.add_parser("upload", help="Upload a file")
        upload_parser.add_argument("local_path", help="Local file path")
        upload_parser.add_argument("url", help="Target URL")
        upload_parser.add_argument("--content-type", help="Content type")
        
        # Download command
        download_parser = file_subparsers.add_parser("download", help="Download a file")
        download_parser.add_argument("url", help="File URL")
        download_parser.add_argument("local_path", help="Local file path")
        
        return parser
    
    async def _init_clients(self):
        """Initialize the clients"""
        # Create the Solid client
        self.client = SolidClient(
            session_id=None,
            access_token=self.args.token
        )
        
        # Create the OIDC client
        self.oidc_client = SolidOidcClient(
            issuer=None
        )
        
        # Create the file client
        self.file_client = SolidFileClient(
            access_token=self.args.token
        )
    
    async def _close_clients(self):
        """Close the clients"""
        if self.client:
            await self.client.close()
        
        if self.oidc_client:
            await self.oidc_client.close()
        
        if self.file_client:
            await self.file_client.close()
    
    async def _handle_auth_login(self):
        """Handle the auth login command"""
        try:
            # Create an authorization URL
            auth_url_data = await self.oidc_client.create_authorization_url(
                issuer=self.args.issuer
            )
            
            # Print the authorization URL
            print(f"Please visit the following URL to login:")
            print(auth_url_data["authorization_url"])
            print(f"\nState: {auth_url_data['state']}")
            
            # Wait for the user to complete the login
            print("\nAfter logging in, you will be redirected to the callback URL.")
            print("Please enter the full callback URL:")
            callback_url = input("> ")
            
            # Parse the callback URL
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(callback_url)
            query_params = parse_qs(parsed_url.query)
            
            # Extract the code and state
            code = query_params.get("code", [""])[0]
            state = query_params.get("state", [""])[0]
            
            if not code:
                print("Error: No authorization code found in the callback URL")
                return
            
            # Exchange the code for tokens
            tokens = await self.oidc_client.exchange_code_for_tokens(
                code=code,
                state=state,
                expected_state=auth_url_data["state"]
            )
            
            # Print the tokens
            print("\nAuthentication successful!")
            print(f"Access token: {tokens['access_token']}")
            print(f"Token type: {tokens['token_type']}")
            print(f"Expires in: {tokens.get('expires_in', 'N/A')} seconds")
            
            if "refresh_token" in tokens:
                print(f"Refresh token: {tokens['refresh_token']}")
            
            if "webid" in tokens:
                print(f"WebID: {tokens['webid']}")
            
            # Save the tokens to a file
            tokens_file = Path("solid_tokens.json")
            with open(tokens_file, "w") as f:
                json.dump(tokens, f, indent=2)
            
            print(f"\nTokens saved to {tokens_file}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_auth_register(self):
        """Handle the auth register command"""
        try:
            # Register with the identity provider
            registration = await self.oidc_client.register_client(
                issuer=self.args.issuer
            )
            
            # Print the registration details
            print("\nRegistration successful!")
            print(f"Client ID: {registration['client_id']}")
            
            if "client_secret" in registration:
                print(f"Client secret: {registration['client_secret']}")
            
            # Save the registration to a file
            reg_file = Path("solid_registration.json")
            with open(reg_file, "w") as f:
                json.dump(registration, f, indent=2)
            
            print(f"\nRegistration saved to {reg_file}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_auth_cert(self):
        """Handle the auth cert command"""
        try:
            # Check if we have a WebID
            webid = self.args.webid
            if not webid:
                print("Error: WebID is required")
                return
            
            # Create a WebID-TLS client
            webid_tls = WebIdTlsAuth(webid=webid)
            
            # Generate a certificate
            cert_path, key_path = webid_tls.generate_certificate(
                common_name=self.args.name or "Solid Client"
            )
            
            # Determine the output directory
            output_dir = self.args.output
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy the certificate and key to the output directory
                import shutil
                cert_output = output_dir / "webid.crt"
                key_output = output_dir / "webid.key"
                
                shutil.copy(cert_path, cert_output)
                shutil.copy(key_path, key_output)
                
                cert_path = str(cert_output)
                key_path = str(key_output)
            
            # Print the certificate paths
            print("\nCertificate generated successfully!")
            print(f"Certificate: {cert_path}")
            print(f"Private key: {key_path}")
            
            # Ask if the user wants to update their WebID profile
            print("\nDo you want to update your WebID profile with this certificate? (y/n)")
            update_profile = input("> ").lower() == "y"
            
            if update_profile:
                # Update the WebID profile
                success = await WebIdTlsAuth.update_webid_profile(webid, cert_path)
                
                if success:
                    print("\nWebID profile updated successfully!")
                else:
                    print("\nFailed to update WebID profile")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_pod_info(self):
        """Handle the pod info command"""
        try:
            # Check if we have a WebID
            webid = self.args.webid
            if not webid:
                print("Error: WebID is required")
                return
            
            # Get the pod info
            pod_info = await self.client.get_webid_profile(webid)
            
            # Print the pod info
            print("\nPod information:")
            print(f"WebID: {pod_info['webid']}")
            print(f"Name: {pod_info['name'] or 'N/A'}")
            print(f"Storage: {pod_info['storage'] or 'N/A'}")
            
            if pod_info["image"]:
                print(f"Image: {pod_info['image']}")
            
            if pod_info["friends"]:
                print("\nFriends:")
                for friend in pod_info["friends"]:
                    print(f"  - {friend}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_pod_create(self):
        """Handle the pod create command"""
        try:
            # Check if we have a token
            if not self.args.token:
                print("Error: Access token is required")
                return
            
            # Create the pod
            pod_data = {
                "name": self.args.name,
                "description": self.args.description
            }
            
            # This is a simplified version, as pod creation depends on the specific Solid server
            print("\nCreating pod...")
            print("Note: Pod creation is server-specific and may not be supported by all servers")
            
            # In a real implementation, we would make a request to the server's pod creation endpoint
            print(f"\nPod creation request:")
            print(json.dumps(pod_data, indent=2))
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_file_list(self):
        """Handle the file list command"""
        try:
            # List the folder contents
            resources = await self.file_client.list_folder(self.args.url)
            
            # Print the resources
            print(f"\nContents of {self.args.url}:")
            
            for resource in resources:
                # Format the resource type
                resource_type = "Folder" if resource["is_container"] else "File"
                
                # Format the last modified date
                last_modified = resource.get("last_modified", "N/A")
                
                print(f"{resource_type:<8} {resource['name']:<30} {last_modified}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_file_read(self):
        """Handle the file read command"""
        try:
            # Read the file
            content = await self.file_client.read_file(self.args.url)
            
            # Check if we should save to a file
            if self.args.output:
                # Save to a file
                output_path = Path(self.args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, "wb") as f:
                    f.write(content)
                
                print(f"\nFile saved to {output_path}")
            else:
                # Try to decode as text
                try:
                    text = content.decode("utf-8")
                    print("\nFile content:")
                    print(text)
                except UnicodeDecodeError:
                    print("\nBinary content, use --output to save to a file")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_file_write(self):
        """Handle the file write command"""
        try:
            # Check if the input is a file or content
            input_path = Path(self.args.input)
            
            if input_path.exists():
                # Read from a file
                with open(input_path, "rb") as f:
                    content = f.read()
                
                # Determine the content type
                content_type = self.args.content_type
                if not content_type:
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(str(input_path))
            else:
                # Treat as content
                content = self.args.input
                content_type = self.args.content_type or "text/plain"
            
            # Write the file
            success = await self.file_client.write_file(
                self.args.url,
                content,
                content_type
            )
            
            if success:
                print(f"\nFile written to {self.args.url}")
            else:
                print("\nFailed to write file")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_file_delete(self):
        """Handle the file delete command"""
        try:
            # Delete the file
            success = await self.file_client.delete_file(self.args.url)
            
            if success:
                print(f"\nFile deleted: {self.args.url}")
            else:
                print("\nFailed to delete file")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_file_mkdir(self):
        """Handle the file mkdir command"""
        try:
            # Create the folder
            success = await self.file_client.create_folder(self.args.url)
            
            if success:
                print(f"\nFolder created: {self.args.url}")
            else:
                print("\nFailed to create folder")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_file_copy(self):
        """Handle the file copy command"""
        try:
            # Copy the file
            success = await self.file_client.copy_file(
                self.args.source,
                self.args.target
            )
            
            if success:
                print(f"\nFile copied from {self.args.source} to {self.args.target}")
            else:
                print("\nFailed to copy file")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_file_move(self):
        """Handle the file move command"""
        try:
            # Move the file
            success = await self.file_client.move_file(
                self.args.source,
                self.args.target
            )
            
            if success:
                print(f"\nFile moved from {self.args.source} to {self.args.target}")
            else:
                print("\nFailed to move file")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_file_upload(self):
        """Handle the file upload command"""
        try:
            # Upload the file
            success = await self.file_client.upload_file(
                self.args.local_path,
                self.args.url,
                self.args.content_type
            )
            
            if success:
                print(f"\nFile uploaded from {self.args.local_path} to {self.args.url}")
            else:
                print("\nFailed to upload file")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _handle_file_download(self):
        """Handle the file download command"""
        try:
            # Download the file
            success = await self.file_client.download_file(
                self.args.url,
                self.args.local_path
            )
            
            if success:
                print(f"\nFile downloaded from {self.args.url} to {self.args.local_path}")
            else:
                print("\nFailed to download file")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def run(self, args=None):
        """Run the CLI"""
        # Parse arguments
        self.args = self.parser.parse_args(args)
        
        # Set up logging
        if self.args.verbose:
            # Configure more verbose logging
            import logging
            logging.basicConfig(level=logging.DEBUG)
        
        # Initialize clients
        await self._init_clients()
        
        try:
            # Handle commands
            if self.args.command == "auth":
                if self.args.auth_command == "login":
                    await self._handle_auth_login()
                elif self.args.auth_command == "register":
                    await self._handle_auth_register()
                elif self.args.auth_command == "cert":
                    await self._handle_auth_cert()
                else:
                    self.parser.print_help()
            elif self.args.command == "pod":
                if self.args.pod_command == "info":
                    await self._handle_pod_info()
                elif self.args.pod_command == "create":
                    await self._handle_pod_create()
                else:
                    self.parser.print_help()
            elif self.args.command == "file":
                if self.args.file_command == "list":
                    await self._handle_file_list()
                elif self.args.file_command == "read":
                    await self._handle_file_read()
                elif self.args.file_command == "write":
                    await self._handle_file_write()
                elif self.args.file_command == "delete":
                    await self._handle_file_delete()
                elif self.args.file_command == "mkdir":
                    await self._handle_file_mkdir()
                elif self.args.file_command == "copy":
                    await self._handle_file_copy()
                elif self.args.file_command == "move":
                    await self._handle_file_move()
                elif self.args.file_command == "upload":
                    await self._handle_file_upload()
                elif self.args.file_command == "download":
                    await self._handle_file_download()
                else:
                    self.parser.print_help()
            else:
                self.parser.print_help()
        finally:
            # Close clients
            await self._close_clients()

def main():
    """Main entry point"""
    cli = SolidCli()
    asyncio.run(cli.run())

if __name__ == "__main__":
    main() 