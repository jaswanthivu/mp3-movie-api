import logging
import sqlite3

import pandas as pd

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)

MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]


class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all movie rows in one transaction."""
        clean_df = df.where(pd.notna(df), None)

        connection = get_connection(self.db_path)

        try:
            connection.execute("DELETE FROM movies")

            for _, row in clean_df.iterrows():
                connection.execute(
                    """
                    INSERT INTO movies (
                        title,
                        release_year,
                        rating,
                        genre
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        row["title"],
                        row["release_year"],
                        row["rating"],
                        row["genre"]
                    )
                )

            connection.commit()

            logger.debug(
                f"Stored movies in SQLite: rows={len(clean_df)}"
            )

        except sqlite3.Error:
            connection.rollback()
            raise

        finally:
            connection.close()

    def get(self):
        """Return the four movie columns as a DataFrame, ordered by id."""
        connection = get_connection(self.db_path)

        try:
            rows = connection.execute(
                """
                SELECT title, release_year, rating, genre
                FROM movies
                ORDER BY id
                """
            ).fetchall()

            return pd.DataFrame(
                [dict(row) for row in rows],
                columns=MOVIE_COLUMNS
            )

        finally:
            connection.close()