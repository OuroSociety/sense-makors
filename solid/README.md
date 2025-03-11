# Solid Pod Server (Python)

A Python implementation of a Solid Pod server using FastAPI and RDFLib, with a comprehensive Solid client library.

## Overview

This project provides:

1. A server that interacts with Solid Pods, allowing users to authenticate with Solid identity providers and manage their Pod resources.
2. A client library for interacting with Solid Pods, supporting various authentication methods and file operations.

It serves as a bridge between client applications and Solid Pod servers, providing a RESTful API for common Pod operations.

## Architecture

The application follows a clean architecture pattern with the following components:

1. **Controllers**: Handle HTTP requests and responses
2. **Services**: Implement business logic
3. **Middleware**: Process requests before they reach route handlers
4. **Routes**: Define API endpoints
5. **Utils**: Provide utility functions and helpers
6. **Client**: Provides a comprehensive client library for interacting with Solid Pods

### Flow Diagram

```mermaid
flowchart TD
    Client[Client Application] <--> API[FastAPI]
    API --> Auth[Authentication Controller]
    API --> Pod[Pod Controller]
    Auth --> SessionService[Session Service]
    Pod --> PodService[Pod Service]
    SessionService <--> SolidAuth[Solid Authentication]
    PodService <--> SolidClient[RDFLib Client]
    SolidAuth <--> IdP[Identity Provider]
    SolidClient <--> PodServer[Solid Pod Server]
    
    subgraph "Solid Pod Server"
        API
        Auth
        Pod
        SessionService
        PodService
    end
    
    subgraph "External Services"
        IdP
        PodServer
    end
    
    subgraph "Client"
        Client
    end
    
    style Solid Pod Server fill:#f9f9f9,stroke:#333,stroke-width:2px
    style External Services fill:#e6f7ff,stroke:#333,stroke-width:2px
    style Client fill:#f0f0f0,stroke:#333,stroke-width:2px
```

## Authentication Flow

1. User initiates login through the client application
2. Server creates a session and returns a login URL for the Solid identity provider
3. User authenticates with the identity provider
4. Identity provider redirects back to the server with authentication code
5. Server exchanges the code for access tokens
6. Server stores the session and returns session details to the client
7. Client includes the session ID in subsequent requests

## Pod Management Flow

1. Client sends authenticated requests to the server
2. Server validates the session
3. Server uses RDFLib to interact with the user's Pod
4. Server returns the results to the client

## API Endpoints

### Authentication

- `POST /api/auth/login`: Login to a Solid identity provider
- `POST /api/auth/register`: Register with a Solid identity provider
- `GET /api/auth/callback`: Handle callback from identity provider
- `POST /api/auth/logout`: Logout from the identity provider
- `GET /api/auth/session`: Get current session info

### Pod Management

- `GET /api/pod/info`: Get information about the user's pod
- `POST /api/pod/create`: Create a new pod
- `GET /api/pod/resources`: List resources in a pod
- `POST /api/pod/resources`: Create a new resource in the pod
- `GET /api/pod/resources/{id}`: Get a specific resource from the pod
- `PUT /api/pod/resources/{id}`: Update a specific resource in the pod
- `DELETE /api/pod/resources/{id}`: Delete a specific resource from the pod

## Solid Client Library

The Solid client library provides a comprehensive set of tools for interacting with Solid Pods:

### Authentication Methods

- **WebID-TLS**: Certificate-based authentication using WebID-TLS
- **Solid-OIDC**: OpenID Connect authentication for Solid
- **Client Credentials**: Server-to-server authentication

### Client Modules

- **SolidClient**: Core client for interacting with Solid Pods
- **WebIdTlsAuth**: WebID-TLS authentication client
- **SolidOidcClient**: Solid-OIDC authentication client
- **ClientCredentialsClient**: Client credentials authentication client
- **SolidFileClient**: File operations client

### Command-Line Interface

The client library includes a command-line interface for interacting with Solid Pods:

```bash
# Authentication commands
python -m solid.src.cli auth login --issuer https://login.inrupt.com/
python -m solid.src.cli auth register --issuer https://login.inrupt.com/
python -m solid.src.cli auth cert --webid https://example.org/profile/card#me

# Pod commands
python -m solid.src.cli pod info --webid https://example.org/profile/card#me
python -m solid.src.cli pod create --name my-pod

# File commands
python -m solid.src.cli file list https://example.org/my-pod/
python -m solid.src.cli file read https://example.org/my-pod/file.txt
python -m solid.src.cli file write https://example.org/my-pod/file.txt --input "Hello, Solid!"
python -m solid.src.cli file delete https://example.org/my-pod/file.txt
python -m solid.src.cli file mkdir https://example.org/my-pod/folder/
python -m solid.src.cli file upload local-file.txt https://example.org/my-pod/file.txt
python -m solid.src.cli file download https://example.org/my-pod/file.txt local-file.txt
```

## Setup and Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure environment variables
4. Start the server: `python main.py solid`

## Development

- Run in development mode: `uvicorn src.main:app --reload`
- Run tests: `pytest`
- Run the client CLI: `python main.py solid-client`

## Technologies Used

- Python 3.9+
- FastAPI
- Uvicorn
- RDFLib
- HTTPX
- Pydantic
- Loguru (logging)
- Pytest (testing)
- Cryptography (WebID-TLS)

## License

MIT 