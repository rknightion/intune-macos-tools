"""
Intune macOS Tools Suite
========================
A comprehensive toolkit for managing macOS devices in Microsoft Intune.
"""

__version__ = "1.0.0"
__author__ = "Intune macOS Tools Team"

from .core.auth import AuthManager
from .core.graph_client import GraphClient

__all__ = ['AuthManager', 'GraphClient']