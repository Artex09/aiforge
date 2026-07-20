"""REST API layer (stdlib http.server)."""
from .server import create_server, serve, serve_in_thread

__all__ = ["serve", "create_server", "serve_in_thread"]
