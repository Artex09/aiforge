"""Dashboard package — vanilla HTML/CSS/JS served by the API layer.

Static assets live in ``dashboard/static``. There is no build step and no
external frontend framework; the API server serves these files directly.
"""
import os

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

__all__ = ["STATIC_DIR"]
