"""Unit tests for the TrackTransformer class."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.transform import TrackTransformer


@pytest.fixture
def transformer():
    """Create a TrackTransformer instance."""
    return TrackTransformer()


@pytest.fixture
def sample_tracks_df():
    """Create a sample DataFrame with Spotify tracks data."""
    return pd.DataFrame({
        'track_id': ['track_001', 'track_002', 'track_003', 'track_001', 'track_004'],
        'track_name': ['  Song One  ', 'Song Two', 'Song Three', 'Song One', 'Song Four'],
        'track_popularity': [85, 42, 0, 85, 100],
        'track_duration_ms': [210000, 180000, -5000, 210000, 300000],
        'track_tempo': [120, 85, 150, 120, 60],
        'track_energy': [0.8, 0.5, 1.2, 0.8, 0.1],
        'track_valence': [0.6, 0.3, 0.9, 0.6, 0.05],
        'track_danceability': [0.7, 0.4, 1.1, 0.7, 0.2],
        'track_explicit': [True, False, True, True, False],
        'track_album_id': ['album_001', 'album_002', 'album_003', 'album_001', 'album_004'],
        'track_album_name': ['Album One', 'Album Two', 'Album Three', 'Album One', 'Album Four'],
        'track_album_release_date': ['2023-01-15', '2022-06-20', 'invalid_date', '2023-01-15', '2024-03-10'],
        'artist_id': ['artist_001', 'artist_002', 'artist_003', 'artist_001', 'artist_004'],
        'artist_name': ['Artist One', 'Artist Two', np.nan, 'Artist One', 'Artist Four'],
        'artist_genres': ['pop, rock', 'jazz', '', 'pop, rock', 'electronic, dance, house']
    })


class TestTrackTransformer:
    """Test cases for TrackTransformer."""

    def test_remove_duplicates(self, transformer, sample_tracks_df):
        """Test that duplicates are removed correctly."""
        # Clean text first so duplicates can be detected properly
        df = transformer._clean_text_columns(sample_tracks_df)
        result = transformer._remove_duplicates(df)

        # Should remove 1 duplicate (track_001 appears twice with different whitespace)
        assert len(result) == 4
        assert transformer.transformation_stats['duplicates_removed'] == 1

    def test_clean_text_columns(self, transformer, sample_tracks_df):
        """Test that text columns are cleaned properly."""
        result = transformer._clean_text_columns(sample_tracks_df)

        # Check that whitespace is stripped
        assert result.loc[0, 'track_name'] == 'Song One'

        # Check that 'nan' strings are converted to actual NaN
        assert pd.isna(result.loc[2, 'artist_name'])

    def test_handle_missing_values(self, transformer, sample_tracks_df):
        """Test that missing values are handled correctly."""
        # First clean text to convert 'nan' strings
        df = transformer._clean_text_columns(sample_tracks_df)
        result = transformer._handle_missing_values(df)

        # Check that artist_name NaN was filled
        assert result.loc[2, 'artist_name'] == 'Unknown Artist'

        # Check that numeric NaNs were filled with median
        assert not pd.isna(result['track_popularity']).any()

    def test_convert_data_types(self, transformer, sample_tracks_df):
        """Test that data types are converted correctly."""
        result = transformer._convert_data_types(sample_tracks_df)

        # Check numeric columns
        assert pd.api.types.is_numeric_dtype(result['track_popularity'])
        assert pd.api.types.is_numeric_dtype(result['track_tempo'])

        # Check boolean column
        assert pd.api.types.is_bool_dtype(result['track_explicit'])

        # Check datetime column (invalid dates become NaT)
        assert pd.api.types.is_datetime64_any_dtype(result['track_album_release_date'])

    def test_engineer_features(self, transformer, sample_tracks_df):
        """Test that new features are engineered correctly."""
        # Prepare the dataframe
        df = transformer._clean_text_columns(sample_tracks_df)
        df = transformer._handle_missing_values(df)
        df = transformer._convert_data_types(df)
        result = transformer._engineer_features(df)

        # Check duration conversions
        assert 'track_duration_seconds' in result.columns
        assert 'track_duration_minutes' in result.columns
        assert result.loc[0, 'track_duration_seconds'] == 210.0

        # Check tempo categories
        assert 'track_tempo_category' in result.columns
        assert result.loc[0, 'track_tempo_category'] == 'medium'  # 120 bpm

        # Check energy levels
        assert 'track_energy_level' in result.columns
        assert result.loc[0, 'track_energy_level'] == 'high'  # 0.8 energy

        # Check popularity tiers
        assert 'track_popularity_tier' in result.columns
        assert result.loc[0, 'track_popularity_tier'] == 'hit'  # 85 popularity falls in 75-100 range

        # Check release year extraction
        assert 'track_album_release_year' in result.columns
        assert result.loc[0, 'track_album_release_year'] == 2023

        # Check genre processing
        assert 'genre_list' in result.columns
        assert 'genre_count' in result.columns
        assert result.loc[0, 'genre_list'] == ['pop', 'rock']

    def test_validate_data(self, transformer, sample_tracks_df):
        """Test that data validation works correctly."""
        # Prepare dataframe
        df = transformer._convert_data_types(sample_tracks_df)
        result = transformer._validate_data(df)

        # Check that invalid durations are removed (track_003 had -5000ms)
        assert len(result) == 4
        assert (result['track_duration_ms'] > 0).all()

        # Check that values are clipped to valid ranges
        assert (result['track_popularity'] >= 0).all()
        assert (result['track_popularity'] <= 100).all()
        assert (result['track_energy'] >= 0).all()
        assert (result['track_energy'] <= 1).all()

    def test_get_genre_table(self, transformer, sample_tracks_df):
        """Test that genre table is created correctly."""
        # Full transformation to get genre_list column
        transformed = transformer.transform(sample_tracks_df)
        genre_df = transformer.get_genre_table(transformed)

        # Check structure
        assert 'track_id' in genre_df.columns
        assert 'genre_name' in genre_df.columns

        # Check that genres are properly exploded
        assert len(genre_df) > 0
        assert 'pop' in genre_df['genre_name'].values
        assert 'rock' in genre_df['genre_name'].values

    def test_full_transformation(self, transformer, sample_tracks_df):
        """Test the complete transformation pipeline."""
        result = transformer.transform(sample_tracks_df)

        # Check that transformation completed
        assert len(result) == 3  # 1 duplicate + 1 invalid duration removed
        assert 'track_duration_seconds' in result.columns
        assert 'track_tempo_category' in result.columns
        assert 'track_energy_level' in result.columns
        assert 'track_popularity_tier' in result.columns

        # Check transformation stats
        stats = transformer.get_stats()
        assert stats['rows_input'] == 5
        assert stats['rows_output'] == 3
        assert stats['duplicates_removed'] == 1

    def test_edge_case_empty_dataframe(self, transformer):
        """Test transformation with empty DataFrame."""
        empty_df = pd.DataFrame(columns=['track_id', 'track_name', 'track_popularity'])
        result = transformer.transform(empty_df)

        assert len(result) == 0
        assert transformer.get_stats()['rows_input'] == 0

    def test_edge_case_single_row(self, transformer):
        """Test transformation with single row DataFrame."""
        single_row_df = pd.DataFrame({
            'track_id': ['track_001'],
            'track_name': ['Test Song'],
            'track_popularity': [50],
            'track_duration_ms': [180000],
        })

        result = transformer.transform(single_row_df)

        assert len(result) == 1
        assert result.loc[0, 'track_duration_seconds'] == 180.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
