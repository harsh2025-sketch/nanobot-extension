"""
Media Module - Comprehensive media handling for nanobot.

Provides audio, video, image handling, transcription, and location tracking.
"""

from .handler import (
    MediaHandler,
    MediaFile,
    MediaConfig,
    MediaType,
    ImageFormat,
    AudioFormat,
    VideoFormat,
)
from .location import (
    LocationHandler,
    Location,
    LocationCoordinate,
    Geofence,
    LocationAccuracy,
    LocationProvider,
)

__all__ = [
    "MediaHandler",
    "MediaFile",
    "MediaConfig",
    "MediaType",
    "ImageFormat",
    "AudioFormat",
    "VideoFormat",
    "LocationHandler",
    "Location",
    "LocationCoordinate",
    "Geofence",
    "LocationAccuracy",
    "LocationProvider",
]
