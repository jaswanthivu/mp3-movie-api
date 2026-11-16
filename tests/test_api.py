def test_upload_movies(client, sample_movies_bytes):
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

    data = response.json()

    assert data["rows"] == 20
    assert data["columns"] == 4
    assert data["column_names"] == [
        "title",
        "release_year",
        "rating",
        "genre",
    ]


def test_get_movies(client, uploaded_movies):
    response = client.get(
        "/movies",
        params={"limit": 2},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["data"]) == 2
    assert data["total_rows"] == 20

    assert data["data"][0]["id"] == 1
    assert data["data"][0]["title"] == "Movie A"


def test_search_movies(client, uploaded_movies):
    response = client.get(
        "/movies/search",
        params=[
            ("columns", "title"),
            ("columns", "rating"),
            ("min_rating", 8.5),
            ("limit", 2),
        ],
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    assert data[0]["id"] == 4
    assert data[0]["title"] == "Movie C"
    assert data[0]["rating"] == 9.0

    assert data[1]["id"] == 2
    assert data[1]["title"] == "Movie B"
    assert data[1]["rating"] == 8.5


def test_upload_replaces_collection(
    client,
    sample_movies_bytes,
    uploaded_movies,
):
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

    movies_response = client.get("/movies")

    assert movies_response.status_code == 200
    assert movies_response.json()["total_rows"] == 20