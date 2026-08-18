"""CSV file extractor for Spotify tracks data."""
import logging
from pathlib import Path
from typing import Optional
import pandas as pd

from config.settings import Settings

logger = logging.getLogger(__name__)


class CSVExtractor:
    """Extracts data from CSV files."""

    def __init__(self):
        """Initialize the extractor."""
        self.raw_data_dir = Settings.RAW_DATA_DIR

    def extract(self, filename: str) -> pd.DataFrame:
        """
        Extract data from a CSV file.

        Args:
            filename: Name of the CSV file in data/raw/ directory

        Returns:
            pandas DataFrame with the extracted data

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is empty or invalid
        """
        file_path = self.raw_data_dir / filename

        logger.info(f"Extracting data from {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            df = pd.read_csv(file_path)
            logger.info(f"Successfully extracted {len(df)} rows from {filename}")

            # Basic validation
            if df.empty:
                raise ValueError(f"File {filename} is empty")

            if df.shape[1] == 0:
                raise ValueError(f"File {filename} has no columns")

            # Log basic statistics
            logger.info(f"Columns: {list(df.columns)}")
            logger.info(f"Shape: {df.shape}")

            return df

        except pd.errors.ParserError as e:
            logger.error(f"Failed to parse {filename}: {e}")
            raise ValueError(f"Invalid CSV format in {filename}: {e}")

    def get_available_files(self) -> list:
        """Get list of available CSV files in raw data directory."""
        csv_files = list(self.raw_data_dir.glob("*.csv"))
        return [f.name for f in csv_files]

    def extract_latest(self) -> pd.DataFrame:
        """
        Extract the most recently modified CSV file.

        Returns:
            pandas DataFrame with the extracted data

        Raises:
            FileNotFoundError: If no CSV files exist
        """
        csv_files = self.get_available_files()

        if not csv_files:
            raise FileNotFoundError("No CSV files found in data/raw/ directory")

        # Sort by modification time (most recent first)
        csv_files_with_time = [
            (f, (self.raw_data_dir / f).stat().st_mtime)
            for f in csv_files
        ]
        csv_files_with_time.sort(key=lambda x: x[1], reverse=True)

        latest_file = csv_files_with_time[0][0]
        logger.info(f"Latest file: {latest_file}")

        return self.extract(latest_file)

    def validate_columns(self, df: pd.DataFrame, required_columns: Optional[list] = None) -> bool:
        """
        Validate that DataFrame has required columns.

        Args:
            df: DataFrame to validate
            required_columns: List of required column names

        Returns:
            True if validation passes

        Raises:
            ValueError: If required columns are missing
        """
        if required_columns is None:
            required_columns = ['track_id', 'track_name']

        missing_columns = set(required_columns) - set(df.columns)

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        logger.info("Column validation passed")
        return True
