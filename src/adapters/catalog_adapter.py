import yaml
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CatalogAdapter:
    """Adapter for video catalog operations"""
    
    def __init__(self, catalog_path: str = "config/videos.yaml"):
        self.catalog_path = Path(catalog_path)
        self._catalog = None
        self._load_catalog()
    
    def _load_catalog(self):
        """Load the video catalog from YAML"""
        try:
            with open(self.catalog_path, 'r') as f:
                data = yaml.safe_load(f)
                self._catalog = {video['id']: video for video in data.get('videos', [])}
            
            # Validation
            if not self._catalog:
                raise ValueError("No videos found in catalog")
            
            # Check for duplicate IDs
            if len(self._catalog) != len(data.get('videos', [])):
                raise ValueError("Duplicate video IDs found in catalog")
            
            # Validate video URIs (GCS or HTTPS)
            for video_id, video in self._catalog.items():
                uri = video.get('gcs_uri', '')
                if not (uri.startswith('gs://') or uri.startswith('https://')):
                    raise ValueError(f"Invalid video URI for video {video_id}: {uri}")
            
            logger.info(f"Loaded {len(self._catalog)} videos from catalog")
            
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
            raise
    
    def list_catalog(self) -> List[Dict]:
        """List all videos in catalog"""
        return list(self._catalog.values())
    
    def get_uri(self, video_id: str) -> str:
        """Get GCS URI for a video ID"""
        if video_id not in self._catalog:
            raise KeyError(f"Video ID {video_id} not found in catalog")
        return self._catalog[video_id]['gcs_uri']
    
    def has(self, video_id: str) -> bool:
        """Check if video ID exists in catalog"""
        return video_id in self._catalog
    
    def get_session_type(self, video_id: str) -> str:
        """Get session type for a video ID"""
        if video_id not in self._catalog:
            raise KeyError(f"Video ID {video_id} not found in catalog")
        return self._catalog[video_id].get('session-type', 'Unknown')
    
    def get_metadata(self, video_id: str) -> Dict:
        """Get full metadata for a video ID"""
        if video_id not in self._catalog:
            raise KeyError(f"Video ID {video_id} not found in catalog")
        return self._catalog[video_id].copy()
