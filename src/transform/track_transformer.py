"""Track transformer for cleaning and enriching Spotify tracks data."""
import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class TrackTransformer:
    """Transforms and enriches Spotify tracks data."""

    def __init__(self):
        """Initialize the transformer."""
        self.transformation_stats = {
            'rows_input': 0,
            'rows_output': 0,
            'duplicates_removed': 0,
            'nulls_handled': 0,
        }

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all transformations to the DataFrame.

        Args:
            df: Raw DataFrame from extractor

        Returns:
            Transformed DataFrame
        """
        logger.info("Starting transformation pipeline")
        self.transformation_stats['rows_input'] = len(df)

        # Apply transformations in sequence
        df = self._clean_text_columns(df)
        df = self._remove_duplicates(df)
        df = self._handle_missing_values(df)
        df = self._convert_data_types(df)
        df = self._engineer_features(df)
        df = self._validate_data(df)

        self.transformation_stats['rows_output'] = len(df)
        logger.info(f"Transformation complete: {self.transformation_stats}")

        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate tracks."""
        initial_count = len(df)

        # Remove exact duplicates
        df = df.drop_duplicates()

        # Remove duplicates based on track name and artist (if columns exist)
        if 'track_name' in df.columns and 'artist_name' in df.columns:
            df = df.drop_duplicates(subset=['track_name', 'artist_name'], keep='first')

        removed_count = initial_count - len(df)
        self.transformation_stats['duplicates_removed'] = removed_count

        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate rows")

        return df

    def _clean_text_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean text columns by stripping whitespace and standardizing."""
        text_columns = ['track_name', 'artist_name', 'track_album_name']

        for col in text_columns:
            if col in df.columns:
                # Strip whitespace
                df[col] = df[col].astype(str).str.strip()

                # Replace 'nan' strings with actual NaN
                df[col] = df[col].replace('nan', np.nan)

                logger.debug(f"Cleaned text column: {col}")

        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values based on column importance."""
        initial_nulls = df.isnull().sum().sum()

        # Drop rows where critical columns are missing
        critical_columns = ['track_id', 'track_name']
        existing_critical = [col for col in critical_columns if col in df.columns]
        df = df.dropna(subset=existing_critical)

        # Fill missing numeric values with 0 or median
        numeric_columns = ['track_popularity', 'track_tempo', 'track_energy',
                          'track_valence', 'track_danceability']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(df[col].median() if not df[col].isnull().all() else 0)

        # Fill missing text values
        text_fill_values = {
            'artist_name': 'Unknown Artist',
            'track_album_name': 'Unknown Album',
            'artist_genres': '',
        }
        for col, fill_value in text_fill_values.items():
            if col in df.columns:
                df[col] = df[col].fillna(fill_value)

        final_nulls = df.isnull().sum().sum()
        self.transformation_stats['nulls_handled'] = initial_nulls - final_nulls

        if initial_nulls > final_nulls:
            logger.info(f"Handled {initial_nulls - final_nulls} null values")

        return df

    def _convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert columns to appropriate data types."""
        # Convert numeric columns
        numeric_columns = ['track_popularity', 'track_tempo', 'track_energy',
                          'track_valence', 'track_danceability', 'track_duration_ms']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Convert explicit to boolean
        if 'track_explicit' in df.columns:
            df['track_explicit'] = df['track_explicit'].astype(bool)

        # Convert release date to datetime
        if 'track_album_release_date' in df.columns:
            df['track_album_release_date'] = pd.to_datetime(
                df['track_album_release_date'], errors='coerce'
            )

        logger.debug("Data type conversion complete")
        return df

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create new features from existing data."""
        # Duration conversions
        if 'track_duration_ms' in df.columns:
            df['track_duration_seconds'] = df['track_duration_ms'] / 1000
            df['track_duration_minutes'] = df['track_duration_seconds'] / 60
            logger.debug("Created duration columns")

        # Tempo categories
        if 'track_tempo' in df.columns:
            df['track_tempo_category'] = pd.cut(
                df['track_tempo'],
                bins=[0, 80, 120, float('inf')],
                labels=['slow', 'medium', 'fast'],
                include_lowest=True
            )
            logger.debug("Created tempo categories")

        # Energy level categories
        if 'track_energy' in df.columns:
            df['track_energy_level'] = pd.cut(
                df['track_energy'],
                bins=[0, 0.33, 0.66, 1.0],
                labels=['low', 'medium', 'high'],
                include_lowest=True
            )
            logger.debug("Created energy levels")

        # Popularity tiers
        if 'track_popularity' in df.columns:
            df['track_popularity_tier'] = pd.cut(
                df['track_popularity'],
                bins=[0, 25, 50, 75, 100],
                labels=['obscure', 'niche', 'popular', 'hit'],
                include_lowest=True
            )
            logger.debug("Created popularity tiers")

        # Release year
        if 'track_album_release_date' in df.columns:
            df['track_album_release_year'] = df['track_album_release_date'].dt.year
            logger.debug("Extracted release year")

        # Genre list processing
        if 'artist_genres' in df.columns:
            df['genre_list'] = df['artist_genres'].apply(
                lambda x: [g.strip() for g in str(x).split(',') if g.strip()] if pd.notna(x) else []
            )
            df['genre_count'] = df['genre_list'].apply(len)
            logger.debug("Processed genres")

        return df

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate data ranges and fix anomalies."""
        # Ensure positive durations
        if 'track_duration_ms' in df.columns:
            invalid_duration = df['track_duration_ms'] <= 0
            if invalid_duration.any():
                logger.warning(f"Found {invalid_duration.sum()} tracks with invalid duration")
                df = df[~invalid_duration]

        # Ensure valid popularity range (0-100)
        if 'track_popularity' in df.columns:
            df['track_popularity'] = df['track_popularity'].clip(0, 100)

        # Ensure valid energy/valence/danceability range (0-1)
        for col in ['track_energy', 'track_valence', 'track_danceability']:
            if col in df.columns:
                df[col] = df[col].clip(0, 1)

        logger.debug("Data validation complete")
        return df

    def get_genre_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract genre information into a separate table format.

        Args:
            df: Transformed DataFrame with genre_list column

        Returns:
            DataFrame with track_id and genre_name columns
        """
        if 'genre_list' not in df.columns:
            logger.warning("genre_list column not found")
            return pd.DataFrame(columns=['track_id', 'genre_name'])

        # Explode genres into separate rows
        genre_df = df[['track_id', 'genre_list']].copy()
        genre_df = genre_df.explode('genre_list')
        genre_df = genre_df.rename(columns={'genre_list': 'genre_name'})
        genre_df = genre_df.dropna(subset=['genre_name'])
        genre_df = genre_df[genre_df['genre_name'] != '']

        logger.info(f"Extracted {len(genre_df)} genre records")
        return genre_df

    def get_stats(self) -> dict:
        """Get transformation statistics."""
        return self.transformation_stats.copy()
