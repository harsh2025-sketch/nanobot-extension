"""
Browser Profile Manager - Persistent session management for browser automation.

Manages browser profiles, cookies, local storage, and session persistence
to provide consistent browser state across restarts.
"""

import asyncio
import logging
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import sqlite3
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class BrowserCookie:
    """Represents a browser cookie."""
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[float] = None
    http_only: bool = False
    secure: bool = False
    same_site: str = "Lax"


@dataclass
class LocalStorageEntry:
    """Represents a localStorage entry."""
    key: str
    value: str
    domain: str


@dataclass
class BrowserProfile:
    """Represents a browser profile."""
    profile_id: str
    profile_name: str
    created_at: datetime
    last_used: datetime
    cookies: List[BrowserCookie] = field(default_factory=list)
    storage: Dict[str, str] = field(default_factory=dict)
    bookmarks: Dict[str, str] = field(default_factory=dict)
    extensions: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)


class BrowserProfileManager:
    """
    Manages browser profiles for persistent session management.
    
    Features:
    - Profile creation and management
    - Cookie persistence and restoration
    - LocalStorage/SessionStorage management
    - Browser preferences/settings
    - Extension management
    - automatic cleanup of expired data
    - Profile encryption (optional)
    - Session replay and restore
    """

    def __init__(self, profile_dir: str):
        """
        Initialize profile manager.
        
        Args:
            profile_dir: Directory to store browser profiles
        """
        self.profile_dir = profile_dir
        self.profiles: Dict[str, BrowserProfile] = {}
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure profile directory exists."""
        os.makedirs(self.profile_dir, exist_ok=True)
        logger.info(f"Profile directory ensured: {self.profile_dir}")

    async def create_profile(
        self,
        profile_name: str,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Optional[BrowserProfile]:
        """
        Create a new browser profile.
        
        Args:
            profile_name: Name for the profile
            preferences: Initial browser preferences
            
        Returns:
            Created profile
        """
        try:
            import uuid
            profile_id = str(uuid.uuid4())
            
            profile = BrowserProfile(
                profile_id=profile_id,
                profile_name=profile_name,
                created_at=datetime.now(),
                last_used=datetime.now(),
                preferences=preferences or {},
            )
            
            self.profiles[profile_id] = profile
            await self._save_profile(profile)
            
            logger.info(f"Created profile: {profile_name} (ID: {profile_id})")
            return profile
        except Exception as e:
            logger.error(f"Failed to create profile: {e}")
            return None

    async def load_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """Load a profile from disk."""
        try:
            profile_file = os.path.join(self.profile_dir, f"{profile_id}.json")
            
            if not os.path.exists(profile_file):
                return None
            
            with open(profile_file, 'r') as f:
                data = json.load(f)
            
            profile = BrowserProfile(
                profile_id=data["profile_id"],
                profile_name=data["profile_name"],
                created_at=datetime.fromisoformat(data["created_at"]),
                last_used=datetime.fromisoformat(data["last_used"]),
                cookies=[
                    BrowserCookie(
                        name=c["name"],
                        value=c["value"],
                        domain=c["domain"],
                        path=c.get("path", "/"),
                        expires=c.get("expires"),
                        http_only=c.get("http_only", False),
                        secure=c.get("secure", False),
                        same_site=c.get("same_site", "Lax"),
                    )
                    for c in data.get("cookies", [])
                ],
                storage=data.get("storage", {}),
                bookmarks=data.get("bookmarks", {}),
                extensions=data.get("extensions", []),
                preferences=data.get("preferences", {}),
            )
            
            self.profiles[profile_id] = profile
            logger.info(f"Loaded profile: {profile.profile_name}")
            return profile
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")
            return None

    async def get_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """Get a profile by ID."""
        if profile_id in self.profiles:
            return self.profiles[profile_id]
        
        return await self.load_profile(profile_id)

    async def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile."""
        try:
            if profile_id in self.profiles:
                del self.profiles[profile_id]
            
            profile_file = os.path.join(self.profile_dir, f"{profile_id}.json")
            if os.path.exists(profile_file):
                os.remove(profile_file)
            
            logger.info(f"Deleted profile: {profile_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete profile: {e}")
            return False

    async def add_cookie(
        self,
        profile_id: str,
        cookie: BrowserCookie,
    ) -> bool:
        """Add a cookie to a profile."""
        try:
            profile = await self.get_profile(profile_id)
            if not profile:
                return False
            
            # Remove existing cookie with same name/domain
            profile.cookies = [
                c for c in profile.cookies
                if not (c.name == cookie.name and c.domain == cookie.domain)
            ]
            
            profile.cookies.append(cookie)
            await self._save_profile(profile)
            
            return True
        except Exception as e:
            logger.error(f"Failed to add cookie: {e}")
            return False

    async def get_cookies(
        self,
        profile_id: str,
        domain: Optional[str] = None,
    ) -> List[BrowserCookie]:
        """Get cookies from a profile."""
        try:
            profile = await self.get_profile(profile_id)
            if not profile:
                return []
            
            cookies = profile.cookies
            
            if domain:
                cookies = [c for c in cookies if c.domain == domain]
            
            return cookies
        except Exception as e:
            logger.error(f"Failed to get cookies: {e}")
            return []

    async def clear_cookies(
        self,
        profile_id: str,
        domain: Optional[str] = None,
    ) -> bool:
        """Clear cookies from a profile."""
        try:
            profile = await self.get_profile(profile_id)
            if not profile:
                return False
            
            if domain:
                profile.cookies = [c for c in profile.cookies if c.domain != domain]
            else:
                profile.cookies = []
            
            await self._save_profile(profile)
            return True
        except Exception as e:
            logger.error(f"Failed to clear cookies: {e}")
            return False

    async def set_local_storage(
        self,
        profile_id: str,
        key: str,
        value: str,
    ) -> bool:
        """Set a localStorage entry."""
        try:
            profile = await self.get_profile(profile_id)
            if not profile:
                return False
            
            profile.storage[key] = value
            await self._save_profile(profile)
            
            return True
        except Exception as e:
            logger.error(f"Failed to set localStorage: {e}")
            return False

    async def get_local_storage(
        self,
        profile_id: str,
        key: Optional[str] = None,
    ) -> Dict[str, str]:
        """Get localStorage entries."""
        try:
            profile = await self.get_profile(profile_id)
            if not profile:
                return {}
            
            if key:
                return {key: profile.storage.get(key, "")}
            
            return profile.storage.copy()
        except Exception as e:
            logger.error(f"Failed to get localStorage: {e}")
            return {}

    async def clear_local_storage(self, profile_id: str) -> bool:
        """Clear all localStorage."""
        try:
            profile = await self.get_profile(profile_id)
            if not profile:
                return False
            
            profile.storage.clear()
            await self._save_profile(profile)
            
            return True
        except Exception as e:
            logger.error(f"Failed to clear localStorage: {e}")
            return False

    async def add_bookmark(
        self,
        profile_id: str,
        name: str,
        url: str,
    ) -> bool:
        """Add a bookmark."""
        try:
            profile = await self.get_profile(profile_id)
            if not profile:
                return False
            
            profile.bookmarks[name] = url
            await self._save_profile(profile)
            
            return True
        except Exception as e:
            logger.error(f"Failed to add bookmark: {e}")
            return False

    async def get_bookmarks(self, profile_id: str) -> Dict[str, str]:
        """Get all bookmarks."""
        try:
            profile = await self.get_profile(profile_id)
            if not profile:
                return {}
            
            return profile.bookmarks.copy()
        except Exception as e:
            logger.error(f"Failed to get bookmarks: {e}")
            return {}

    async def cleanup_expired_data(self, profile_id: str) -> int:
        """Remove expired cookies from a profile."""
        try:
            profile = await self.get_profile(profile_id)
            if not profile:
                return 0
            
            now = datetime.now().timestamp()
            original_count = len(profile.cookies)
            
            profile.cookies = [
                c for c in profile.cookies
                if c.expires is None or c.expires > now
            ]
            
            removed = original_count - len(profile.cookies)
            
            if removed > 0:
                await self._save_profile(profile)
            
            logger.info(f"Removed {removed} expired cookies")
            return removed
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0

    async def list_profiles(self) -> List[BrowserProfile]:
        """List all available profiles."""
        try:
            profiles = []
            
            # Load from disk
            for filename in os.listdir(self.profile_dir):
                if filename.endswith(".json"):
                    profile_id = filename[:-5]
                    profile = await self.load_profile(profile_id)
                    if profile:
                        profiles.append(profile)
            
            return profiles
        except Exception as e:
            logger.error(f"Failed to list profiles: {e}")
            return []

    async def export_profile(
        self,
        profile_id: str,
        export_path: str,
    ) -> bool:
        """Export profile to file."""
        try:
            profile = await self.get_profile(profile_id)
            if not profile:
                return False
            
            data = {
                "profile_id": profile.profile_id,
                "profile_name": profile.profile_name,
                "created_at": profile.created_at.isoformat(),
                "last_used": profile.last_used.isoformat(),
                "cookies": [
                    {
                        "name": c.name,
                        "value": c.value,
                        "domain": c.domain,
                        "path": c.path,
                        "expires": c.expires,
                        "http_only": c.http_only,
                        "secure": c.secure,
                        "same_site": c.same_site,
                    }
                    for c in profile.cookies
                ],
                "storage": profile.storage,
                "bookmarks": profile.bookmarks,
                "extensions": profile.extensions,
                "preferences": profile.preferences,
            }
            
            with open(export_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported profile to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export profile: {e}")
            return False

    async def import_profile(
        self,
        import_path: str,
        profile_name: Optional[str] = None,
    ) -> Optional[BrowserProfile]:
        """Import profile from file."""
        try:
            with open(import_path, 'r') as f:
                data = json.load(f)
            
            import uuid
            profile_id = str(uuid.uuid4())
            
            profile = BrowserProfile(
                profile_id=profile_id,
                profile_name=profile_name or data.get("profile_name", "Imported"),
                created_at=datetime.now(),
                last_used=datetime.now(),
                cookies=[
                    BrowserCookie(
                        name=c["name"],
                        value=c["value"],
                        domain=c["domain"],
                        path=c.get("path", "/"),
                        expires=c.get("expires"),
                        http_only=c.get("http_only", False),
                        secure=c.get("secure", False),
                        same_site=c.get("same_site", "Lax"),
                    )
                    for c in data.get("cookies", [])
                ],
                storage=data.get("storage", {}),
                bookmarks=data.get("bookmarks", {}),
                extensions=data.get("extensions", []),
                preferences=data.get("preferences", {}),
            )
            
            self.profiles[profile_id] = profile
            await self._save_profile(profile)
            
            logger.info(f"Imported profile: {profile.profile_name}")
            return profile
        except Exception as e:
            logger.error(f"Failed to import profile: {e}")
            return None

    async def _save_profile(self, profile: BrowserProfile) -> None:
        """Save profile to disk."""
        try:
            profile_file = os.path.join(self.profile_dir, f"{profile.profile_id}.json")
            
            data = {
                "profile_id": profile.profile_id,
                "profile_name": profile.profile_name,
                "created_at": profile.created_at.isoformat(),
                "last_used": profile.last_used.isoformat(),
                "cookies": [
                    {
                        "name": c.name,
                        "value": c.value,
                        "domain": c.domain,
                        "path": c.path,
                        "expires": c.expires,
                        "http_only": c.http_only,
                        "secure": c.secure,
                        "same_site": c.same_site,
                    }
                    for c in profile.cookies
                ],
                "storage": profile.storage,
                "bookmarks": profile.bookmarks,
                "extensions": profile.extensions,
                "preferences": profile.preferences,
            }
            
            with open(profile_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")


__all__ = [
    "BrowserProfileManager",
    "BrowserProfile",
    "BrowserCookie",
    "LocalStorageEntry",
]
