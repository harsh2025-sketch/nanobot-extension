"""
UltraBot — A superior personal AI agent framework.
Multi-channel, offline-capable, with local neurosymbolic fallback, system-level automation, and platform node support.
"""

from importlib.metadata import version as _version, PackageNotFoundError as _PNF

try:
    __version__ = _version("nanobot-ai")
except _PNF:
    __version__ = "0.2.0"

__logo__ = "[nb]"
__display_name__ = "UltraBot"
__author__ = "ultrabot contributors"

__all__ = ["__version__", "__logo__", "__display_name__", "__author__"]
