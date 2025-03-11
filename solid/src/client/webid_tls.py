import os
import ssl
import httpx
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta
import rdflib
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import FOAF, RDF

from ..utils.exceptions import ApiError
from ..utils.logger import logger

class WebIdTlsAuth:
    """
    WebID-TLS authentication client
    
    This client provides methods for authenticating with Solid servers using WebID-TLS,
    as specified in the W3C WebID-TLS specification.
    """
    
    def __init__(self, webid: str = None):
        """
        Initialize the WebID-TLS authentication client
        
        Args:
            webid: Optional WebID URL
        """
        self.webid = webid
        self.cert_path = None
        self.key_path = None
    
    def generate_certificate(self, common_name: str = None) -> Tuple[str, str]:
        """
        Generate a self-signed certificate for WebID-TLS authentication
        
        Args:
            common_name: Optional common name for the certificate
            
        Returns:
            Tuple[str, str]: Paths to the certificate and key files
        """
        # Create a temporary directory for the certificate and key
        temp_dir = Path(tempfile.mkdtemp())
        
        # Generate a private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Write the private key to a file
        key_path = temp_dir / "webid.key"
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Create a self-signed certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name or "WebID-TLS Client"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([x509.URI(self.webid)]),
            critical=False
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Write the certificate to a file
        cert_path = temp_dir / "webid.crt"
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Store the paths
        self.cert_path = str(cert_path)
        self.key_path = str(key_path)
        
        return self.cert_path, self.key_path
    
    def create_ssl_context(self) -> ssl.SSLContext:
        """
        Create an SSL context for WebID-TLS authentication
        
        Returns:
            ssl.SSLContext: SSL context with the certificate and key
            
        Raises:
            ApiError: If the certificate or key is not available
        """
        if not self.cert_path or not self.key_path:
            raise ApiError("Certificate and key not available")
        
        # Create an SSL context
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(self.cert_path, self.key_path)
        
        return context
    
    async def authenticate(self, url: str) -> bool:
        """
        Authenticate with a Solid server using WebID-TLS
        
        Args:
            url: URL of the Solid server
            
        Returns:
            bool: True if authentication is successful
            
        Raises:
            ApiError: If authentication fails
        """
        if not self.cert_path or not self.key_path:
            raise ApiError("Certificate and key not available")
        
        try:
            # Create an HTTP client with the certificate
            client = httpx.AsyncClient(
                verify=False,  # Skip verification for self-signed certificates
                cert=(self.cert_path, self.key_path)
            )
            
            # Make a request to the server
            response = await client.get(url)
            
            # Check if authentication was successful
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Authentication failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise ApiError(f"Authentication error: {str(e)}")
        finally:
            await client.aclose()
    
    @staticmethod
    async def update_webid_profile(webid: str, cert_path: str) -> bool:
        """
        Update a WebID profile with a certificate
        
        Args:
            webid: WebID URL
            cert_path: Path to the certificate file
            
        Returns:
            bool: True if successful
            
        Raises:
            ApiError: If the update fails
        """
        try:
            # Read the certificate
            with open(cert_path, "rb") as f:
                cert_data = f.read()
            
            # Parse the certificate
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Get the public key
            public_key = cert.public_key()
            
            # Convert the public key to a modulus and exponent
            public_numbers = public_key.public_numbers()
            modulus = public_numbers.n
            exponent = public_numbers.e
            
            # Create a graph for the WebID profile
            g = Graph()
            
            # Add namespaces
            CERT = rdflib.Namespace("http://www.w3.org/ns/auth/cert#")
            g.bind("cert", CERT)
            g.bind("foaf", FOAF)
            
            # Create a blank node for the RSA key
            key = BNode()
            
            # Add the RSA key to the profile
            g.add((URIRef(webid), CERT.key, key))
            g.add((key, RDF.type, CERT.RSAPublicKey))
            g.add((key, CERT.modulus, Literal(format(modulus, "x"))))
            g.add((key, CERT.exponent, Literal(exponent)))
            
            # Make a request to update the profile
            client = httpx.AsyncClient()
            
            try:
                # Get the current profile
                response = await client.get(webid, headers={"Accept": "text/turtle"})
                
                if response.status_code == 200:
                    # Parse the current profile
                    current_profile = Graph()
                    current_profile.parse(data=response.text, format="turtle")
                    
                    # Merge the new key into the current profile
                    for triple in g:
                        current_profile.add(triple)
                    
                    # Update the profile
                    response = await client.put(
                        webid,
                        headers={"Content-Type": "text/turtle"},
                        content=current_profile.serialize(format="turtle")
                    )
                    
                    return response.status_code in [200, 201, 204]
                else:
                    logger.error(f"Failed to get profile: {response.text}")
                    return False
            finally:
                await client.aclose()
        except Exception as e:
            logger.error(f"Error updating WebID profile: {str(e)}")
            raise ApiError(f"Error updating WebID profile: {str(e)}")
    
    @staticmethod
    def extract_webid_from_certificate(cert_path: str) -> Optional[str]:
        """
        Extract the WebID from a certificate
        
        Args:
            cert_path: Path to the certificate file
            
        Returns:
            Optional[str]: WebID URL or None if not found
        """
        try:
            # Read the certificate
            with open(cert_path, "rb") as f:
                cert_data = f.read()
            
            # Parse the certificate
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Get the Subject Alternative Name extension
            for extension in cert.extensions:
                if extension.oid == x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
                    san = extension.value
                    
                    # Look for a URI in the SAN
                    for uri in san.get_values_for_type(x509.URI):
                        return uri
            
            return None
        except Exception as e:
            logger.error(f"Error extracting WebID from certificate: {str(e)}")
            return None 