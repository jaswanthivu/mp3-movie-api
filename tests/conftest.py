from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app, storage
from src.database import initialize_database


@pytest.fixture
def client(tmp_path):
    original_db_path = storage.db_path

    storage.db_path = tmp_path / "test_movies.db"
    initialize_database(storage.db_path)

    with TestClient(app) as test_client:
        yield test_client

    storage.db_path = original_db_path


@pytest.fixture
def sample_movies_bytes():
    filepath = Path("fixtures") / "sample_movies.csv"
    return filepath.read_bytes()


@pytest.fixture
def uploaded_movies(client, sample_movies_bytes):
    response = client.post(
        "/upload",
        files={
            "file": (
                "sample_movies.csv",
                sample_movies_bytes,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    return response