#!/usr/bin/env python3
"""
Spotify Tracks ETL Pipeline
Main entry point for extracting, transforming, and loading Spotify tracks data.
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from config.settings import Settings
from src.extract import CSVExtractor
from src.transform import TrackTransformer
from src.load import PostgresLoader


def setup_logging(log_level: str = None) -> None:
    """Configure logging for the pipeline."""
    if log_level is None:
        log_level = Settings.LOG_LEVEL

    # Create logs directory
    Settings.ensure_directories()

    # Configure logging
    log_file = Settings.LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Spotify Tracks ETL Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                           # Run with default settings
  python run_pipeline.py --input tracks.csv       # Specify input file
  python run_pipeline.py --skip-load              # Extract and transform only
  python run_pipeline.py --log-level DEBUG        # Enable debug logging
        """
    )

    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Input CSV filename (from data/raw/ directory)'
    )

    parser.add_argument(
        '--skip-load',
        action='store_true',
        help='Skip the load phase (extract and transform only)'
    )

    parser.add_argument(
        '--skip-create-tables',
        action='store_true',
        help='Skip table creation (use existing schema)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=Settings.BATCH_SIZE,
        help=f'Batch size for database inserts (default: {Settings.BATCH_SIZE})'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=None,
        help='Set logging level'
    )

    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> None:
    """
    Execute the ETL pipeline.

    Args:
        args: Command-line arguments
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Starting Spotify Tracks ETL Pipeline")
    logger.info("=" * 60)

    start_time = datetime.now()

    # Initialize components
    extractor = CSVExtractor()
    transformer = TrackTransformer()
    loader = PostgresLoader()

    try:
        # ===== EXTRACT =====
        logger.info("\n📥 EXTRACT PHASE")
        logger.info("-" * 40)

        # Get input file
        if args.input:
            input_file = args.input
        else:
            available_files = extractor.get_available_files()
            if not available_files:
                raise FileNotFoundError(
                    "No CSV files found in data/raw/ directory. "
                    "Please add your Spotify dataset CSV file there."
                )
            input_file = available_files[0]
            logger.info(f"Auto-selected file: {input_file}")

        # Extract data
        raw_df = extractor.extract(input_file)
        logger.info(f"Extracted {len(raw_df)} rows")

        # Validate columns
        required_columns = ['track_id', 'track_name']
        try:
            extractor.validate_columns(raw_df, required_columns)
        except ValueError as e:
            logger.warning(f"Column validation warning: {e}")
            logger.info("Continuing with available columns...")

        # ===== TRANSFORM =====
        logger.info("\n🔄 TRANSFORM PHASE")
        logger.info("-" * 40)

        transformed_df = transformer.transform(raw_df)
        genre_df = transformer.get_genre_table(transformed_df)

        stats = transformer.get_stats()
        logger.info(f"Transformation statistics: {stats}")

        # Save processed data to CSV for reference
        processed_file = Settings.PROCESSED_DATA_DIR / f"processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        transformed_df.to_csv(processed_file, index=False)
        logger.info(f"Saved processed data to: {processed_file}")

        # ===== LOAD =====
        if not args.skip_load:
            logger.info("\n💾 LOAD PHASE")
            logger.info("-" * 40)

            # Connect to database
            loader.connect()

            # Create tables if needed
            if not args.skip_create_tables:
                loader.create_tables()

            # Load data
            tracks_loaded = loader.load_tracks(transformed_df, batch_size=args.batch_size)
            genres_loaded = loader.load_genres(genre_df)

            # Log pipeline run
            loader.log_pipeline_run(
                records_extracted=len(raw_df),
                records_transformed=len(transformed_df),
                records_loaded=tracks_loaded,
                status='success'
            )

            # Get final counts
            counts = loader.get_table_counts()
            logger.info(f"\nFinal table counts: {counts}")

        else:
            logger.info("\n⏭️  Skipping LOAD phase (--skip-load flag)")

        # ===== SUMMARY =====
        end_time = datetime.now()
        duration = end_time - start_time

        logger.info("\n" + "=" * 60)
        logger.info("Pipeline completed successfully!")
        logger.info("=" * 60)
        logger.info(f"Duration: {duration.total_seconds():.2f} seconds")
        logger.info(f"Records extracted: {len(raw_df)}")
        logger.info(f"Records transformed: {len(transformed_df)}")
        if not args.skip_load:
            logger.info(f"Records loaded: {tracks_loaded}")
        logger.info(f"Processed data saved to: {processed_file}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)

        # Log error to metadata if connected
        if loader.connection:
            loader.log_pipeline_run(
                records_extracted=0,
                records_transformed=0,
                records_loaded=0,
                status='error',
                error_message=str(e)
            )

        sys.exit(1)

    finally:
        # Cleanup
        if loader.connection:
            loader.disconnect()


def main():
    """Main entry point."""
    # Ensure directories exist
    Settings.ensure_directories()

    # Parse arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(args.log_level)

    # Run pipeline
    run_pipeline(args)


if __name__ == '__main__':
    main()
