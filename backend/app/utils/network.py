from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Direct peer address. Behind a reverse proxy, configure proxy/uvicorn forwarded-ip handling."""
    return request.client.host if request.client else "unknown"
