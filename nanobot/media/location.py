"""
Location Handler - Geolocation tracking and location services integration.

Provides location tracking, GPS data, geofencing, and location-based services.
"""

import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class LocationAccuracy(Enum):
    """Location accuracy levels."""
    HIGH = "high"       # GPS, ~5-10 meters
    MEDIUM = "medium"   # Network, ~100 meters
    LOW = "low"         # Approximate, ~1000 meters
    COARSE = "coarse"   # Very approximate, ~10km


class LocationProvider(Enum):
    """Location data providers."""
    GPS = "gps"
    NETWORK = "network"
    HYBRID = "hybrid"
    WIFI = "wifi"


@dataclass
class LocationCoordinate:
    """Represents a geographic coordinate."""
    latitude: float
    longitude: float
    altitude: Optional[float] = None  # meters
    accuracy: LocationAccuracy = LocationAccuracy.MEDIUM
    timestamp: datetime = field(default_factory=datetime.now)
    provider: LocationProvider = LocationProvider.NETWORK
    speed: Optional[float] = None  # m/s
    heading: Optional[float] = None  # degrees


@dataclass
class Location:
    """Represents a location with details."""
    location_id: str
    coordinate: LocationCoordinate
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    postal_code: str = ""
    timezone: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Geofence:
    """Represents a geofenced area."""
    fence_id: str
    name: str
    center: LocationCoordinate
    radius_meters: float
    active: bool = True
    entered_callback: Optional[Callable] = None
    exited_callback: Optional[Callable] = None


class LocationHandler:
    """
    Location tracking and geolocation services.
    
    Features:
    - GPS tracking and polling
    - Network-based location
    - Hybrid location detection
    - Geofencing with entry/exit triggers
    - Location history
    - Reverse geocoding (coordinates to address)
    - Distance calculation
    - Location-based notifications
    - Privacy controls
    """

    def __init__(self):
        """Initialize location handler."""
        self.enabled = False
        self.current_location: Optional[LocationCoordinate] = None
        self.location_history: List[LocationCoordinate] = []
        self.geofences: Dict[str, Geofence] = {}
        self.location_handlers: List[Callable] = []
        self._tracking_task: Optional[asyncio.Task] = None
        self._max_history = 1000

    async def initialize(self) -> bool:
        """Initialize location handler."""
        try:
            logger.info("Location handler initialized")
            self.enabled = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize location handler: {e}")
            return False

    async def start_tracking(
        self,
        accuracy: LocationAccuracy = LocationAccuracy.MEDIUM,
        update_interval: int = 5,  # seconds
    ) -> bool:
        """
        Start continuous location tracking.
        
        Args:
            accuracy: Desired accuracy level
            update_interval: Update interval in seconds
            
        Returns:
            Success status
        """
        try:
            if self._tracking_task:
                return False

            self._tracking_task = asyncio.create_task(
                self._track_location_loop(update_interval)
            )
            
            logger.info(f"Location tracking started (interval: {update_interval}s)")
            return True
        except Exception as e:
            logger.error(f"Failed to start tracking: {e}")
            return False

    async def stop_tracking(self) -> bool:
        """Stop location tracking."""
        try:
            if not self._tracking_task:
                return False

            self._tracking_task.cancel()
            try:
                await self._tracking_task
            except asyncio.CancelledError:
                pass
            
            self._tracking_task = None
            logger.info("Location tracking stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop tracking: {e}")
            return False

    async def get_current_location(
        self,
        force_update: bool = False,
    ) -> Optional[LocationCoordinate]:
        """Get current location."""
        try:
            if force_update or not self.current_location:
                self.current_location = await self._fetch_location()
                
                if self.current_location:
                    self._add_to_history(self.current_location)
            
            return self.current_location
        except Exception as e:
            logger.error(f"Failed to get current location: {e}")
            return None

    async def get_location_address(
        self,
        coordinate: LocationCoordinate,
    ) -> Optional[Location]:
        """
        Reverse geocode coordinates to address.
        
        Args:
            coordinate: Latitude/longitude
            
        Returns:
            Location with address details
        """
        try:
            import uuid
            location_id = str(uuid.uuid4())

            # Simulate geocoding
            location = Location(
                location_id=location_id,
                coordinate=coordinate,
                address="123 Main Street",
                city="San Francisco",
                state="CA",
                country="United States",
                postal_code="94103",
                timezone="America/Los_Angeles",
            )

            logger.info(f"Geocoded location: {location.city}, {location.state}")
            return location
        except Exception as e:
            logger.error(f"Failed to geocode location: {e}")
            return None

    def calculate_distance(
        self,
        from_coord: LocationCoordinate,
        to_coord: LocationCoordinate,
    ) -> float:
        """
        Calculate distance between two coordinates (Haversine formula).
        
        Args:
            from_coord: Starting coordinate
            to_coord: Ending coordinate
            
        Returns:
            Distance in meters
        """
        try:
            R = 6371000  # Earth radius in meters
            
            lat1 = math.radians(from_coord.latitude)
            lat2 = math.radians(to_coord.latitude)
            delta_lat = math.radians(to_coord.latitude - from_coord.latitude)
            delta_lon = math.radians(to_coord.longitude - from_coord.longitude)
            
            a = math.sin(delta_lat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance = R * c
            
            return distance
        except Exception as e:
            logger.error(f"Failed to calculate distance: {e}")
            return 0.0

    async def add_geofence(
        self,
        name: str,
        center: LocationCoordinate,
        radius_meters: float,
        entered_callback: Optional[Callable] = None,
        exited_callback: Optional[Callable] = None,
    ) -> Optional[str]:
        """
        Add a geofence.
        
        Args:
            name: Geofence name
            center: Center point
            radius_meters: Radius in meters
            entered_callback: Callback when entered
            exited_callback: Callback when exited
            
        Returns:
            Geofence ID
        """
        try:
            import uuid
            fence_id = str(uuid.uuid4())
            
            geofence = Geofence(
                fence_id=fence_id,
                name=name,
                center=center,
                radius_meters=radius_meters,
                entered_callback=entered_callback,
                exited_callback=exited_callback,
            )
            
            self.geofences[fence_id] = geofence
            logger.info(f"Geofence added: {name} ({radius_meters}m)")
            
            return fence_id
        except Exception as e:
            logger.error(f"Failed to add geofence: {e}")
            return None

    async def remove_geofence(self, fence_id: str) -> bool:
        """Remove a geofence."""
        try:
            if fence_id not in self.geofences:
                return False

            geofence = self.geofences[fence_id]
            del self.geofences[fence_id]
            
            logger.info(f"Geofence removed: {geofence.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove geofence: {e}")
            return False

    def register_location_handler(self, handler: Callable) -> None:
        """Register a location update handler."""
        self.location_handlers.append(handler)

    def get_location_history(
        self,
        limit: Optional[int] = None,
    ) -> List[LocationCoordinate]:
        """Get location history."""
        if limit:
            return self.location_history[-limit:]
        return self.location_history.copy()

    def clear_location_history(self) -> None:
        """Clear location history."""
        self.location_history.clear()
        logger.info("Location history cleared")

    async def shutdown(self) -> None:
        """Shutdown location handler."""
        await self.stop_tracking()
        self.geofences.clear()
        logger.info("Location handler shutdown")

    def _add_to_history(self, coordinate: LocationCoordinate) -> None:
        """Add coordinate to history."""
        self.location_history.append(coordinate)
        
        # Trim history if needed
        if len(self.location_history) > self._max_history:
            self.location_history = self.location_history[-self._max_history:]

    async def _track_location_loop(self, update_interval: int) -> None:
        """Continuously track location."""
        while True:
            try:
                # Get new location
                self.current_location = await self._fetch_location()
                
                if self.current_location:
                    self._add_to_history(self.current_location)
                    
                    # Check geofences
                    await self._check_geofences(self.current_location)
                    
                    # Call handlers
                    for handler in self.location_handlers:
                        try:
                            await handler(self.current_location)
                        except Exception as e:
                            logger.error(f"Handler error: {e}")
                
                await asyncio.sleep(update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Tracking error: {e}")
                await asyncio.sleep(update_interval)

    async def _fetch_location(self) -> Optional[LocationCoordinate]:
        """Fetch current location."""
        try:
            # Simulate location fetch
            await asyncio.sleep(0.1)
            
            # Return simulated location
            return LocationCoordinate(
                latitude=37.7749,
                longitude=-122.4194,
                altitude=10.0,
                accuracy=LocationAccuracy.MEDIUM,
                provider=LocationProvider.NETWORK,
            )
        except Exception as e:
            logger.error(f"Failed to fetch location: {e}")
            return None

    async def _check_geofences(self, coordinate: LocationCoordinate) -> None:
        """Check if current location is in any geofence."""
        try:
            for geofence in self.geofences.values():
                if not geofence.active:
                    continue

                distance = self.calculate_distance(coordinate, geofence.center)
                is_inside = distance <= geofence.radius_meters

                # Track state changes
                was_inside = getattr(geofence, '_was_inside', False)
                geofence._was_inside = is_inside

                if is_inside and not was_inside:
                    # Entered geofence
                    if geofence.entered_callback:
                        try:
                            await geofence.entered_callback(geofence, coordinate)
                        except Exception as e:
                            logger.error(f"Geofence callback error: {e}")
                elif not is_inside and was_inside:
                    # Exited geofence
                    if geofence.exited_callback:
                        try:
                            await geofence.exited_callback(geofence, coordinate)
                        except Exception as e:
                            logger.error(f"Geofence callback error: {e}")
        except Exception as e:
            logger.error(f"Error checking geofences: {e}")


__all__ = [
    "LocationHandler",
    "Location",
    "LocationCoordinate",
    "Geofence",
    "LocationAccuracy",
    "LocationProvider",
]
