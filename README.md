# Spotify Tracks ETL Pipeline

A production-quality ETL (Extract, Transform, Load) pipeline for processing Spotify tracks data. This project extracts track data from CSV files, applies comprehensive transformations and feature engineering, and loads the enriched data into a PostgreSQL database.

## Features

- **Modular Architecture**: Clean separation of Extract, Transform, and Load phases
- **Comprehensive Transformations**:
  - Duplicate detection and removal
  - Missing value handling with intelligent imputation
  - Data type conversion and validation
  - Feature engineering (duration, tempo categories, energy levels, popularity tiers)
  - Genre extraction and normalization
- **PostgreSQL Integration**: Robust database loading with batch inserts and upsert logic
- **Pipeline Metadata**: Automatic logging of execution statistics
- **Configurable**: Environment-based configuration for database and pipeline settings
- **Well-Tested**: Unit tests for transformation logic
- **Logging**: Detailed execution logs for monitoring and debugging

## Project Structure

```
Spotify Track Dataset/
├── config/
│   ├── __init__.py
│   └── settings.py              # Configuration management
├── src/
│   ├── __init__.py
│   ├── extract/
│   │   ├── __init__.py
│   │   └── csv_extractor.py     # CSV file extraction
│   ├── transform/
│   │   ├── __init__.py
│   │   └── track_transformer.py # Data cleaning & transformation
│   └── load/
│       ├── __init__.py
│       └── postgres_loader.py   # PostgreSQL loading
├── data/
│   ├── raw/                     # Place your CSV files here
│   └── processed/               # Transformed data exports
├── logs/                        # Pipeline execution logs
├── tests/
│   ├── __init__.py
│   └── test_transformer.py      # Unit tests
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
├── run_pipeline.py              # Main entry point
└── README.md                    # This file
```

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

## Installation

1. **Clone the repository** (or download the project files):
   ```bash
   cd "E:\Projects\Project-4\Spotify Track Dataset"
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database**:
   ```sql
   CREATE DATABASE spotify_tracks;
   ```

5. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` file with your database credentials:
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=spotify_tracks
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

## Data Preparation

1. **Download a Spotify Tracks Dataset** from Kaggle:
   - Recommended: [Spotify Tracks Dataset](https://www.kaggle.com/datasets/mahfuzurrahmanbd/spotify-tracks-dataset)
   - Or any similar dataset with track information

2. **Place the CSV file** in the `data/raw/` directory:
   ```
   data/raw/your_dataset.csv
   ```

3. **Expected columns** (minimum required):
   - `track_id` - Unique identifier for each track
   - `track_name` - Name of the track

   **Recommended columns for full feature engineering**:
   - `track_popularity` - Popularity score (0-100)
   - `track_duration_ms` - Duration in milliseconds
   - `track_tempo` - Tempo in BPM
   - `track_energy` - Energy score (0-1)
   - `track_valence` - Valence score (0-1)
   - `track_danceability` - Danceability score (0-1)
   - `track_explicit` - Whether the track is explicit
   - `track_album_id`, `track_album_name`, `track_album_release_date`
   - `artist_id`, `artist_name`, `artist_genres`

## Usage

### Basic Usage

Run the pipeline with default settings:
```bash
python run_pipeline.py
```

### Command-Line Options

```bash
# Specify input file
python run_pipeline.py --input spotify_tracks.csv

# Skip database loading (extract and transform only)
python run_pipeline.py --skip-load

# Enable debug logging
python run_pipeline.py --log-level DEBUG

# Custom batch size for database inserts
python run_pipeline.py --batch-size 500

# Skip table creation (use existing schema)
python run_pipeline.py --skip-create-tables
```

### Run Tests

```bash
pytest tests/ -v
```

## Pipeline Stages

### 1. Extract Phase
- Loads CSV file from `data/raw/` directory
- Validates file existence and structure
- Logs basic statistics (row count, columns)

### 2. Transform Phase
- **Duplicate Removal**: Identifies and removes duplicate tracks
- **Text Cleaning**: Strips whitespace, standardizes text fields
- **Missing Values**: Intelligently handles null values based on column importance
- **Data Type Conversion**: Ensures correct data types for all columns
- **Feature Engineering**:
  - Converts duration from milliseconds to seconds and minutes
  - Categorizes tempo (slow/medium/fast)
  - Creates energy levels (low/medium/high)
  - Assigns popularity tiers (obscure/niche/popular/hit)
  - Extracts release year from date
  - Processes genre lists
- **Data Validation**: Ensures values are within valid ranges

### 3. Load Phase
- Connects to PostgreSQL database
- Creates tables with proper schema and indexes
- Performs batch inserts with upsert logic (avoids duplicates)
- Loads genre data into separate normalized table
- Logs pipeline execution metadata

## Database Schema

### tracks table
| Column | Type | Description |
|--------|------|-------------|
| track_id | VARCHAR(255) | Primary key |
| track_name | VARCHAR(500) | Track title |
| track_popularity | INTEGER | Popularity score (0-100) |
| track_duration_seconds | FLOAT | Duration in seconds |
| track_duration_minutes | FLOAT | Duration in minutes |
| track_tempo | FLOAT | Tempo in BPM |
| track_tempo_category | VARCHAR(20) | slow/medium/fast |
| track_energy | FLOAT | Energy score (0-1) |
| track_energy_level | VARCHAR(20) | low/medium/high |
| track_valence | FLOAT | Valence score (0-1) |
| track_danceability | FLOAT | Danceability score (0-1) |
| track_popularity_tier | VARCHAR(20) | obscure/niche/popular/hit |
| track_explicit | BOOLEAN | Explicit content flag |
| track_album_id | VARCHAR(255) | Album identifier |
| track_album_name | VARCHAR(500) | Album name |
| track_album_release_date | DATE | Release date |
| track_album_release_year | INTEGER | Release year |
| artist_id | VARCHAR(255) | Artist identifier |
| artist_name | VARCHAR(500) | Artist name |
| created_at | TIMESTAMP | Record creation time |

### genres table
| Column | Type | Description |
|--------|------|-------------|
| genre_id | SERIAL | Primary key |
| track_id | VARCHAR(255) | Foreign key to tracks |
| genre_name | VARCHAR(255) | Genre name |

### pipeline_metadata table
| Column | Type | Description |
|--------|------|-------------|
| run_id | SERIAL | Primary key |
| run_timestamp | TIMESTAMP | Execution timestamp |
| records_extracted | INTEGER | Records from source |
| records_transformed | INTEGER | Records after transformation |
| records_loaded | INTEGER | Records loaded to database |
| status | VARCHAR(50) | success/error |
| error_message | TEXT | Error details if failed |

## Sample Queries

Once data is loaded, you can run analytics queries:

```sql
-- Top 10 most popular tracks
SELECT track_name, artist_name, track_popularity
FROM tracks
ORDER BY track_popularity DESC
LIMIT 10;

-- Average track duration by tempo category
SELECT track_tempo_category,
       AVG(track_duration_minutes) as avg_duration_minutes
FROM tracks
GROUP BY track_tempo_category;

-- Most common genres
SELECT genre_name, COUNT(*) as genre_count
FROM genres
GROUP BY genre_name
ORDER BY genre_count DESC
LIMIT 20;

-- Tracks by energy level and popularity
SELECT track_energy_level,
       track_popularity_tier,
       COUNT(*) as track_count
FROM tracks
GROUP BY track_energy_level, track_popularity_tier
ORDER BY track_count DESC;

-- Average popularity by release year
SELECT track_album_release_year,
       AVG(track_popularity) as avg_popularity,
       COUNT(*) as track_count
FROM tracks
WHERE track_album_release_year IS NOT NULL
GROUP BY track_album_release_year
ORDER BY track_album_release_year;
```

## Configuration

Configuration is managed through environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| DB_HOST | localhost | PostgreSQL host |
| DB_PORT | 5432 | PostgreSQL port |
| DB_NAME | spotify_tracks | Database name |
| DB_USER | postgres | Database user |
| DB_PASSWORD | - | Database password |
| LOG_LEVEL | INFO | Logging level |
| BATCH_SIZE | 1000 | Batch size for inserts |

## Logs

Pipeline execution logs are stored in the `logs/` directory with timestamps:
```
logs/pipeline_20240115_143022.log
```

Logs include:
- Execution start/end times
- Phase-by-phase progress
- Transformation statistics
- Error details (if any)
- Performance metrics

## Future Enhancements

Potential improvements for this pipeline:

- **Apache Airflow Integration**: Orchestrate with DAGs for scheduling
- **Spotify API Integration**: Extract data directly from Spotify Web API
- **Data Quality Checks**: Add Great Expectations or similar validation
- **Incremental Loading**: Support for appending new data without duplicates
- **Docker Containerization**: Easy deployment with Docker Compose
- **dbt Models**: Add analytics-ready transformations
- **Dashboard Integration**: Connect to Grafana or Tableau for visualization
- **API Layer**: FastAPI endpoints for querying the data

## Troubleshooting

### Common Issues

1. **"No CSV files found"**
   - Ensure your CSV file is in `data/raw/` directory
   - Check file permissions

2. **Database connection errors**
   - Verify PostgreSQL is running
   - Check `.env` file credentials
   - Ensure database `spotify_tracks` exists

3. **Column validation warnings**
   - Pipeline will continue with available columns
   - Check if your dataset has the expected column names

4. **Memory issues with large datasets**
   - Reduce `BATCH_SIZE` in `.env`
   - Consider sampling the data first

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for the full text.
