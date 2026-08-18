"""Configuration settings for the ETL pipeline."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Central configuration class."""

    # Base paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / 'data'
    RAW_DATA_DIR = DATA_DIR / 'raw'
    PROCESSED_DATA_DIR = DATA_DIR / 'processed'
    LOG_DIR = BASE_DIR / 'logs'

    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'spotify_tracks')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    # Pipeline configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', 1000))

    # CSV column mappings (adjust based on your dataset)
    COLUMN_MAPPINGS = {
        'track_id': 'track_id',
        'track_name': 'track_name',
        'track_popularity': 'track_popularity',
        'track_duration_ms': 'track_duration_ms',
        'track_explicit': 'track_explicit',
        'track_album_id': 'track_album_id',
        'track_album_name': 'track_album_name',
        'track_album_release_date': 'track_album_release_date',
        'artist_id': 'artist_id',
        'artist_name': 'artist_name',
        'artist_genres': 'artist_genres',
        'track_tempo': 'track_tempo',
        'track_energy': 'track_energy',
        'track_valence': 'track_valence',
        'track_danceability': 'track_danceability',
    }

    @classmethod
    def get_database_url(cls) -> str:
        """Get PostgreSQL connection URL."""
        return (
            f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        for directory in [cls.DATA_DIR, cls.RAW_DATA_DIR, cls.PROCESSED_DATA_DIR, cls.LOG_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
