import os
from pathlib import Path
from datetime import datetime

def setup_media_structure(base_path: str = 'media') -> None:
    """
    Create the required directory structure for media files.
    If directories already exist, they will be skipped.
    
    Args:
        base_path (str): Base path where the media directory will be created
    """
    # Current year and month for the directory structure
    current_year = datetime.now().strftime('%Y')
    current_month = datetime.now().strftime('%m')
    
    # Define all required directories
    directories = [
        os.path.join(base_path, current_year, current_month, 'orders', 'attachments'),
        os.path.join(base_path, current_year, current_month, 'orders', 'akt'),
        os.path.join(base_path, current_year, current_month, 'reports'),
        os.path.join(base_path, current_year, current_month, 'exports'),
        os.path.join(base_path, 'temp'),
        os.path.join(base_path, 'system', 'videos'),
        os.path.join(base_path, 'system', 'logs')
    ]
    
    # Create each directory if it doesn't exist
    for directory in directories:
        try:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            # Only print message if it's not the temp directory
            if 'temp' not in path.parts:
                print(f"Directory created or already exists: {directory}")
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
            raise
