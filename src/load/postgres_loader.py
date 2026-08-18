"""PostgreSQL loader for Spotify tracks data."""
import logging
from datetime import datetime
from typing import Optional
import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from config.settings import Settings

logger = logging.getLogger(__name__)


class PostgresLoader:
    """Loads transformed data into PostgreSQL database."""

    def __init__(self):
        """Initialize the loader with database connection."""
        self.connection = None
        self.cursor = None

    def connect(self) -> None:
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(
                host=Settings.DB_HOST,
                port=Settings.DB_PORT,
                database=Settings.DB_NAME,
                user=Settings.DB_USER,
                password=Settings.DB_PASSWORD
            )
            self.cursor = self.connection.cursor()
            logger.info("Successfully connected to PostgreSQL database")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Database connection closed")

    def create_tables(self) -> None:
        """Create database schema if it doesn't exist."""
        create_tracks_table = """
        CREATE TABLE IF NOT EXISTS tracks (
            track_id VARCHAR(255) PRIMARY KEY,
            track_name VARCHAR(500) NOT NULL,
            track_popularity INTEGER,
            track_duration_seconds FLOAT,
            track_duration_minutes FLOAT,
            track_tempo FLOAT,
            track_tempo_category VARCHAR(20),
            track_energy FLOAT,
            track_energy_level VARCHAR(20),
            track_valence FLOAT,
            track_danceability FLOAT,
            track_popularity_tier VARCHAR(20),
            track_explicit BOOLEAN,
            track_album_id VARCHAR(255),
            track_album_name VARCHAR(500),
            track_album_release_date DATE,
            track_album_release_year INTEGER,
            artist_id VARCHAR(255),
            artist_name VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        create_genres_table = """
        CREATE TABLE IF NOT EXISTS genres (
            genre_id SERIAL PRIMARY KEY,
            track_id VARCHAR(255) NOT NULL,
            genre_name VARCHAR(255) NOT NULL,
            FOREIGN KEY (track_id) REFERENCES tracks(track_id) ON DELETE CASCADE
        );
        """

        create_metadata_table = """
        CREATE TABLE IF NOT EXISTS pipeline_metadata (
            run_id SERIAL PRIMARY KEY,
            run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            records_extracted INTEGER,
            records_transformed INTEGER,
            records_loaded INTEGER,
            status VARCHAR(50),
            error_message TEXT
        );
        """

        # Create index for faster queries
        create_indexes = """
        CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist_name);
        CREATE INDEX IF NOT EXISTS idx_tracks_popularity ON tracks(track_popularity);
        CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(track_album_id);
        CREATE INDEX IF NOT EXISTS idx_genres_track ON genres(track_id);
        CREATE INDEX IF NOT EXISTS idx_genres_name ON genres(genre_name);
        """

        try:
            self.cursor.execute(create_tracks_table)
            self.cursor.execute(create_genres_table)
            self.cursor.execute(create_metadata_table)
            self.cursor.execute(create_indexes)
            self.connection.commit()
            logger.info("Database tables created successfully")
        except psycopg2.Error as e:
            self.connection.rollback()
            logger.error(f"Failed to create tables: {e}")
            raise

    def load_tracks(self, df: pd.DataFrame, batch_size: Optional[int] = None) -> int:
        """
        Load tracks data into the tracks table.

        Args:
            df: Transformed DataFrame with track data
            batch_size: Number of rows to insert per batch

        Returns:
            Number of rows loaded
        """
        if batch_size is None:
            batch_size = Settings.BATCH_SIZE

        # Select only the columns that exist in the database schema
        db_columns = [
            'track_id', 'track_name', 'track_popularity', 'track_duration_seconds',
            'track_duration_minutes', 'track_tempo', 'track_tempo_category',
            'track_energy', 'track_energy_level', 'track_valence', 'track_danceability',
            'track_popularity_tier', 'track_explicit', 'track_album_id',
            'track_album_name', 'track_album_release_date', 'track_album_release_year',
            'artist_id', 'artist_name'
        ]

        # Filter to only columns that exist in the DataFrame
        available_columns = [col for col in db_columns if col in df.columns]
        df_to_insert = df[available_columns].copy()

        # Convert DataFrame to list of tuples
        data = [tuple(row) for row in df_to_insert.values]

        # Prepare insert query
        insert_query = sql.SQL("""
            INSERT INTO tracks ({}) VALUES %s
            ON CONFLICT (track_id) DO UPDATE SET
                track_name = EXCLUDED.track_name,
                track_popularity = EXCLUDED.track_popularity,
                track_duration_seconds = EXCLUDED.track_duration_seconds,
                track_duration_minutes = EXCLUDED.track_duration_minutes,
                updated_at = CURRENT_TIMESTAMP
        """).format(sql.SQL(', ').join(map(sql.Identifier, available_columns)))

        # Add updated_at column if it doesn't exist
        add_updated_at = """
        ALTER TABLE tracks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """
        self.cursor.execute(add_updated_at)

        loaded_count = 0
        try:
            # Insert in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                execute_values(self.cursor, insert_query.as_string(self.connection), batch)
                loaded_count += len(batch)
                logger.debug(f"Inserted batch {i // batch_size + 1}: {len(batch)} rows")

            self.connection.commit()
            logger.info(f"Successfully loaded {loaded_count} tracks")
            return loaded_count

        except psycopg2.Error as e:
            self.connection.rollback()
            logger.error(f"Failed to load tracks: {e}")
            raise

    def load_genres(self, df: pd.DataFrame) -> int:
        """
        Load genre data into the genres table.

        Args:
            df: DataFrame with track_id and genre_name columns

        Returns:
            Number of rows loaded
        """
        if df.empty:
            logger.info("No genres to load")
            return 0

        # Delete existing genre data for these tracks
        track_ids = df['track_id'].unique().tolist()
        delete_query = "DELETE FROM genres WHERE track_id = ANY(%s)"
        self.cursor.execute(delete_query, (track_ids,))

        # Prepare insert query
        insert_query = """
            INSERT INTO genres (track_id, genre_name) VALUES %s
        """

        data = [tuple(row) for row in df[['track_id', 'genre_name']].values]

        try:
            execute_values(self.cursor, insert_query, data, batch_size=Settings.BATCH_SIZE)
            self.connection.commit()
            logger.info(f"Successfully loaded {len(data)} genre records")
            return len(data)
        except psycopg2.Error as e:
            self.connection.rollback()
            logger.error(f"Failed to load genres: {e}")
            raise

    def log_pipeline_run(self, records_extracted: int, records_transformed: int,
                        records_loaded: int, status: str, error_message: Optional[str] = None) -> None:
        """
        Log pipeline execution metadata.

        Args:
            records_extracted: Number of records extracted
            records_transformed: Number of records after transformation
            records_loaded: Number of records loaded to database
            status: Pipeline status ('success' or 'error')
            error_message: Error message if status is 'error'
        """
        insert_query = """
            INSERT INTO pipeline_metadata
            (records_extracted, records_transformed, records_loaded, status, error_message)
            VALUES (%s, %s, %s, %s, %s)
        """

        try:
            self.cursor.execute(insert_query, (
                records_extracted, records_transformed, records_loaded,
                status, error_message
            ))
            self.connection.commit()
            logger.debug("Pipeline run logged to metadata table")
        except psycopg2.Error as e:
            self.connection.rollback()
            logger.error(f"Failed to log pipeline run: {e}")

    def get_table_counts(self) -> dict:
        """Get row counts for all tables."""
        counts = {}
        tables = ['tracks', 'genres', 'pipeline_metadata']

        for table in tables:
            try:
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = self.cursor.fetchone()[0]
            except psycopg2.Error:
                counts[table] = 0

        return counts

    def execute_query(self, query: str) -> list:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL query to execute

        Returns:
            List of tuples with query results
        """
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise
