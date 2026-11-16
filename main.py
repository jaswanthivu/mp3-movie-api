import io
import json
import logging
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from data_pipeline import (
    create_cleaning_report,
    process_data,
    validate_dataframe,
)


from src import (
    HealthResponse,
    ProcessConfig,
    MovieStorage,
    MovieUploadInfo,
    MovieDataResponse,
    MovieProcessingReport,
    setup_logging,
    log_requests,
)

from src.storage import MOVIE_COLUMNS


setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)

storage = MovieStorage()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):
    """Read, validate, and store a movie CSV upload."""

    extension = Path(file.filename or "").suffix.lower()

    if extension != ".csv":
        logger.warning(f"Unsupported file format: {extension}")
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported"
        )

    contents = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError
    ) as error:
        logger.warning(f"Cannot read CSV: {error}")
        raise HTTPException(
            status_code=400,
            detail="Cannot read the uploaded CSV"
        )

    if set(df.columns) != set(MOVIE_COLUMNS) or len(df.columns) != len(MOVIE_COLUMNS):
        raise HTTPException(
            status_code=400,
            detail="CSV must contain exactly the required movie columns"
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain at least one movie"
        )

    df = df[MOVIE_COLUMNS]

    storage.save(df)

    logger.info(
        f"Uploaded movies: filename={file.filename}, rows={len(df)}"
    )

    return {
        "filename": file.filename,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
    }


@app.get("/movies", response_model=MovieDataResponse)
def get_movies(limit: int = Query(default=100, ge=1)):
    """Return up to limit stored movies."""

    total_rows = storage.count_movies()

    if total_rows == 0:
        return {
            "data": [],
            "total_rows": 0
        }

    data = storage.select_columns(MOVIE_COLUMNS, limit)

    logger.info(
        f"Retrieved movies: returned_rows={len(data)}, "
        f"total_rows={total_rows}"
    )

    return {
        "data": data,
        "total_rows": total_rows
    }

@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1)
):
    """Return selected movie fields filtered by minimum rating."""

    try:
        rows = storage.query_movies(columns, min_rating, limit)
    except ValueError as error:
        logger.warning(f"Movie query failed: {error}")
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    logger.info(
        f"Queried movies: columns={columns}, "
        f"min_rating={min_rating}, returned_rows={len(rows)}"
    )

    return rows

@app.post("/movies/process", response_model=MovieProcessingReport)
def process_movies(config: ProcessConfig):
    """Validate and process the stored movie collection."""

    df = storage.get()

    if df.empty:
        logger.warning("No movies available to process")
        raise HTTPException(
            status_code=400,
            detail="No movies available to process"
        )

    config_dict = config.model_dump()

    validation = config_dict["validation"]
    required_columns = validation["required_columns"]
    numeric_columns = validation["numeric_columns"]

    for column in numeric_columns:
        if column not in df.columns:
            logger.warning(f"Numeric column not found: {column}")
            raise HTTPException(
                status_code=400,
                detail=f"Numeric column not found: {column}"
            )

    try:
        rows_before_validation = len(df)

        validated_df = validate_dataframe(
            df,
            required_columns,
            numeric_columns
        )

        validation_rows_removed = (
            rows_before_validation - len(validated_df)
        )

        validated_before_processing = validated_df.copy()

        processed_df = process_data(
            validated_df,
            config_dict
        )

        cleaning_report = create_cleaning_report(
            validated_before_processing,
            processed_df
        )

    except ValueError as error:
        logger.warning(f"Movie processing failed: {error}")
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    storage.save(processed_df)

    logger.info(
        f"Processed movies: "
        f"validation_removed={validation_rows_removed}, "
        f"rows_before={cleaning_report['rows_before']}, "
        f"rows_after={cleaning_report['rows_after']}"
    )

    return {
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report
    }