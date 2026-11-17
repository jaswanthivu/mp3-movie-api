# MP3 Movie API

This project is a FastAPI application for uploading, storing, processing, and retrieving movie data. Movie data is uploaded from a CSV file and saved in a SQLite database so it stays available even after the server restarts. The API can return stored movies, search for movies using selected columns and a minimum rating, and process the movie data using the data pipeline from earlier projects. The app also uses a cache for repeated `GET /movies` requests so the same data does not have to be read from the database every time. The cache is cleared whenever a new CSV is uploaded or the stored movies are processed so old results are not returned. The project also includes tests for database persistence, cache behavior, and processing.

## Run the API

```bash
python -m uvicorn main:app --reload

```
## Run the Tests

```bash
python -m pytest tests -v
```

## Example Processing Request

```json
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {
      "enabled": true,
      "columns": ["rating"],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}
```

## Expected Result

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```
