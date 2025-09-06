"""
Configuration settings for ETH Research Collection Dashboard.
"""

import os
from pathlib import Path
from typing import Optional

class Config:
    """Application configuration."""
    
    # API Settings
    API_BASE_URL = "https://api.library.ethz.ch/research-collection/v2/discover/search/objects"
    DEFAULT_MAX_ITEMS = 150
    DEFAULT_GROUP_ID = "09746"
    
    # Data Settings
    DATA_DIR = Path("data")
    CACHE_DIR = DATA_DIR / "cache"
    OUTPUT_DIR = DATA_DIR / "output"
    
    # File Names
    CSV_OUTPUT = "ghe-research-collection.csv"
    EXCEL_OUTPUT = "ghe-research-collection.xlsx"
    JSON_CACHE = "api_response_cache.json"
    
    # Display Settings
    PUBLICATION_TYPES = {
        'student': ['Student Paper', 'Bachelor Thesis', 'Master Thesis'],
        'dataset': ['Dataset', 'Data Collection'],
        'article': ['Journal Article', 'Review Article', 'Book Chapter']
    }
    
    LICENSE_MAPPING = {
        'Creative Commons Attribution 4.0 International': 'CC BY 4.0',
        'Creative Commons Attribution-NonCommercial 4.0 International': 'CC BY-NC 4.0',
        'In Copyright - Non-Commercial Use Permitted': 'Copyright',
        'Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International': 'CC BY-NC-ND 4.0',
        'Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International': 'CC BY-NC-SA 4.0'
    }
    
    # Filter Settings
    MIN_YEAR = 2010
    
    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """Get API key from environment."""
        return os.getenv('ETH_RC_API_KEY')
    
    @classmethod
    def get_group_id(cls) -> str:
        """Get group ID from environment or use default."""
        return os.getenv('ETH_RC_GROUP_ID', cls.DEFAULT_GROUP_ID)
    
    @classmethod
    def get_max_items(cls) -> int:
        """Get max items from environment or use default."""
        try:
            return int(os.getenv('ETH_RC_MAX_ITEMS', cls.DEFAULT_MAX_ITEMS))
        except ValueError:
            return cls.DEFAULT_MAX_ITEMS
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)
        cls.OUTPUT_DIR.mkdir(exist_ok=True)