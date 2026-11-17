import pytest

import main
from src import MovieStorage


def test_movies_persist(
    client,
    test_storage,
    uploaded_movies,
    sample_csv_bytes,
):
    other_storage = MovieStorage(test_storage.db_path)

    df = other_storage.get()

    assert len(df) == 20
    assert list(df.columns) == [
        "title",
        "release_year",
        "rating",
        "genre",
    ]

    import pandas as pd
    import io

    original_df = pd.read_csv(io.BytesIO(sample_csv_bytes))

    assert df["title"].tolist() == original_df["title"].tolist()

    stored_rows = other_storage.select_columns(
        ["title", "release_year", "rating", "genre"],
        limit=100,
    )

    response = client.get(
        "/movies",
        params={"limit": 100},
    )

    assert response.status_code == 200

    api_rows = response.json()["data"]

    assert [row["id"] for row in stored_rows] == list(range(1, 21))
    assert [row["id"] for row in api_rows] == list(range(1, 21))


def test_cache_and_processing(
    client,
    uploaded_movies,
    processing_body,
):
    response_100 = client.get(
        "/movies",
        params={"limit": 100},
    )

    assert response_100.status_code == 200
    assert main.cache.get(100) == response_100.json()

    response_1 = client.get(
        "/movies",
        params={"limit": 1},
    )

    assert response_1.status_code == 200
    assert main.cache.get(1) == response_1.json()

    repeated_response = client.get(
        "/movies",
        params={"limit": 100},
    )

    assert repeated_response.status_code == 200
    assert repeated_response.json() == response_100.json()

    process_response = client.post(
        "/movies/process",
        json=processing_body,
    )

    assert process_response.status_code == 200

    process_data = process_response.json()

    assert process_data["validation_rows_removed"] == 0
    assert process_data["cleaning_report"]["rows_before"] == 20
    assert process_data["cleaning_report"]["rows_after"] == 16
    assert process_data["cleaning_report"]["rows_removed"] == 4

    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    updated_response = client.get(
        "/movies",
        params={"limit": 100},
    )

    assert updated_response.status_code == 200

    updated_data = updated_response.json()

    assert updated_data["total_rows"] == 16
    assert [row["title"] for row in updated_data["data"]] == [
        f"Movie {letter}"
        for letter in "ABCDEFGHIJKLMNOP"
    ]
    assert [row["id"] for row in updated_data["data"]] == list(range(1, 17))

    assert main.cache.get(100) == updated_data


def test_cache_hit_skips_database(
    client,
    uploaded_movies,
    monkeypatch,
):
    first_response = client.get(
        "/movies",
        params={"limit": 100},
    )

    assert first_response.status_code == 200
    first_data = first_response.json()

    def fail_if_called(*args, **kwargs):
        pytest.fail("Database should not be accessed on a cache hit")

    monkeypatch.setattr(
        main.storage,
        "select_columns",
        fail_if_called,
    )
    monkeypatch.setattr(
        main.storage,
        "count_movies",
        fail_if_called,
    )

    second_response = client.get(
        "/movies",
        params={"limit": 100},
    )

    assert second_response.status_code == 200
    assert second_response.json() == first_data