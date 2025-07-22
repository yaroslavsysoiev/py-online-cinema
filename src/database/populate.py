import asyncio
import math
from typing import List, Dict, Tuple

import pandas as pd
from sqlalchemy import insert, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from tqdm import tqdm

from config import get_settings
from database import (
    CountryModel,
    GenreModel,
    ActorModel,
    MoviesGenresModel,
    ActorsMoviesModel,
    LanguageModel,
    MoviesLanguagesModel,
    MovieModel, UserGroupModel, UserGroupEnum
)
from database import get_db_contextmanager

CHUNK_SIZE = 1000


class CSVDatabaseSeeder:
    """
    A class responsible for seeding the database from a CSV file using asynchronous SQLAlchemy.
    """

    def __init__(self, csv_file_path: str, db_session: AsyncSession) -> None:
        """
        Initialize the seeder with the path to the CSV file and an async database session.

        :param csv_file_path: The path to the CSV file containing movie data.
        :param db_session: An instance of AsyncSession for performing database operations.
        """
        self._csv_file_path = csv_file_path
        self._db_session = db_session

    async def is_db_populated(self) -> bool:
        """
        Check if the MovieModel table has at least one record.

        :return: True if there's already at least one movie in the database, otherwise False.
        """
        result = await self._db_session.execute(select(MovieModel).limit(1))
        first_movie = result.scalars().first()
        return first_movie is not None

    def _preprocess_csv(self) -> pd.DataFrame:
        """
        Load the CSV, remove duplicates, convert relevant columns to strings, and clean up data.
        Saves the cleaned CSV back to the same path, then returns the Pandas DataFrame.

        :return: A Pandas DataFrame containing cleaned movie data.
        """
        data = pd.read_csv(self._csv_file_path)
        data = data.drop_duplicates(subset=['names', 'date_x'], keep='first')

        for col in ['crew', 'genre', 'country', 'orig_lang', 'status']:
            data[col] = data[col].fillna('Unknown').astype(str)

        data['crew'] = (
            data['crew']
            .str.replace(r'\s+', '', regex=True)
            .apply(lambda x: ','.join(sorted(set(x.split(',')))) if x != 'Unknown' else x)
        )

        data['genre'] = data['genre'].str.replace('\u00A0', '', regex=True)
        data['date_x'] = data['date_x'].astype(str).str.strip()
        data['date_x'] = pd.to_datetime(data['date_x'], format='%Y-%m-%d', errors='raise')
        data['date_x'] = data['date_x'].dt.date
        data['orig_lang'] = data['orig_lang'].str.replace(r'\s+', '', regex=True)
        data['status'] = data['status'].str.strip()

        print("Preprocessing CSV file...")
        data.to_csv(self._csv_file_path, index=False)
        print(f"CSV file saved to {self._csv_file_path}")
        return data

    async def _seed_user_groups(self) -> None:
        """
        Seed the UserGroupModel table with default user groups if none exist.

        This method checks whether any user groups are already present in the database.
        If no records are found, it inserts all groups defined in the UserGroupEnum.
        After insertion, the changes are flushed to the current transaction.
        """
        count_stmt = select(func.count(UserGroupModel.id))
        result = await self._db_session.execute(count_stmt)
        existing_groups = result.scalar()

        if existing_groups == 0:
            groups = [{"name": group.value} for group in UserGroupEnum]
            await self._db_session.execute(insert(UserGroupModel).values(groups))
            await self._db_session.flush()

            print("User groups seeded successfully.")

    async def _get_or_create_bulk(
            self,
            model,
            items: List[str],
            unique_field: str
    ) -> Dict[str, object]:
        """
        For a given model and a list of item names/keys (e.g., a list of genres),
        retrieves any existing records in the database matching these items.
        If some items are not found, they are created in bulk. Returns a dictionary
        mapping the item string to the corresponding model instance.

        :param model: The SQLAlchemy model class (e.g., GenreModel).
        :param items: A list of string values to create or retrieve (e.g., ["Comedy", "Action"]).
        :param unique_field: The field name that should be unique (e.g., "name").
        :return: A dict mapping each item to its model instance.
        """
        existing_dict: Dict[str, object] = {}

        if items:
            for i in range(0, len(items), CHUNK_SIZE):
                chunk = items[i: i + CHUNK_SIZE]
                result = await self._db_session.execute(
                    select(model).where(getattr(model, unique_field).in_(chunk))
                )
                existing_in_chunk = result.scalars().all()
                for obj in existing_in_chunk:
                    key = getattr(obj, unique_field)
                    existing_dict[key] = obj

        new_items = [item for item in items if item not in existing_dict]
        new_records = [{unique_field: item} for item in new_items]

        if new_records:
            for i in range(0, len(new_records), CHUNK_SIZE):
                chunk = new_records[i: i + CHUNK_SIZE]
                await self._db_session.execute(insert(model).values(chunk))
                await self._db_session.flush()

            for i in range(0, len(new_items), CHUNK_SIZE):
                chunk = new_items[i: i + CHUNK_SIZE]
                result_new = await self._db_session.execute(
                    select(model).where(getattr(model, unique_field).in_(chunk))
                )
                inserted_in_chunk = result_new.scalars().all()
                for obj in inserted_in_chunk:
                    key = getattr(obj, unique_field)
                    existing_dict[key] = obj

        return existing_dict

    async def _bulk_insert(self, table, data_list: List[Dict[str, int]]) -> None:
        """
        Insert data_list into the given table in chunks, displaying progress via tqdm.

        :param table: The SQLAlchemy table or model to insert into.
        :param data_list: A list of dictionaries, where each dict represents a row to insert.
        """
        total_records = len(data_list)
        if total_records == 0:
            return

        num_chunks = math.ceil(total_records / CHUNK_SIZE)
        table_name = getattr(table, '__tablename__', str(table))

        for chunk_index in tqdm(range(num_chunks), desc=f"Inserting into {table_name}"):
            start = chunk_index * CHUNK_SIZE
            end = start + CHUNK_SIZE
            chunk = data_list[start:end]
            if chunk:
                await self._db_session.execute(insert(table).values(chunk))

        await self._db_session.flush()

    async def _prepare_reference_data(
            self,
            data: pd.DataFrame
    ) -> Tuple[Dict[str, object], Dict[str, object], Dict[str, object], Dict[str, object]]:
        """
        Gather unique values for countries, genres, actors, and languages from the DataFrame.
        Then call _get_or_create_bulk for each to ensure they exist in the database.

        :param data: The preprocessed Pandas DataFrame containing movie info.
        :return: A tuple of four dictionaries:
                 (country_map, genre_map, actor_map, language_map).
        """
        countries = list(data['country'].unique())
        genres = {
            genre.strip()
            for genres_ in data['genre'].dropna() for genre in genres_.split(',')
            if genre.strip()
        }
        actors = {
            actor.strip()
            for crew in data['crew'].dropna() for actor in crew.split(',')
            if actor.strip()
        }
        languages = {
            lang.strip()
            for langs in data['orig_lang'].dropna() for lang in langs.split(',')
            if lang.strip()
        }

        country_map = await self._get_or_create_bulk(CountryModel, countries, 'code')
        genre_map = await self._get_or_create_bulk(GenreModel, list(genres), 'name')
        actor_map = await self._get_or_create_bulk(ActorModel, list(actors), 'name')
        language_map = await self._get_or_create_bulk(LanguageModel, list(languages), 'name')

        return country_map, genre_map, actor_map, language_map

    def _prepare_movies_data(
            self,
            data: pd.DataFrame,
            country_map: Dict[str, object]
    ) -> List[Dict[str, object]]:
        """
        Build a list of dictionaries representing movie records to be inserted into MovieModel.

        :param data: The preprocessed DataFrame.
        :param country_map: A mapping of country codes to CountryModel instances.
        :return: A list of dictionaries, each representing a new movie record.
        """
        movies_data: List[Dict[str, object]] = []
        for _, row in tqdm(data.iterrows(), total=data.shape[0], desc="Processing movies"):
            country = country_map[row['country']]
            movie = {
                "name": row['names'],
                "date": row['date_x'],
                "score": float(row['score']),
                "overview": row['overview'],
                "status": row['status'],
                "budget": float(row['budget_x']),
                "revenue": float(row['revenue']),
                "country_id": country.id
            }
            movies_data.append(movie)
        return movies_data

    def _prepare_associations(
            self,
            data: pd.DataFrame,
            movie_ids: List[int],
            genre_map: Dict[str, object],
            actor_map: Dict[str, object],
            language_map: Dict[str, object]
    ) -> Tuple[List[Dict[str, int]], List[Dict[str, int]], List[Dict[str, int]]]:
        """
        Prepare three lists of dictionaries: movie-genre, movie-actor, and movie-language
        associations for all movies in the DataFrame.

        :param data: The DataFrame containing movie info.
        :param movie_ids: The list of newly inserted movie IDs, in the same order as DataFrame rows.
        :param genre_map: A mapping of genre names to GenreModel instances.
        :param actor_map: A mapping of actor names to ActorModel instances.
        :param language_map: A mapping of language names to LanguageModel instances.
        :return: A tuple of three lists:
                 (movie_genres_data, movie_actors_data, movie_languages_data),
                 each containing dictionaries for bulk insertion.
        """
        movie_genres_data: List[Dict[str, int]] = []
        movie_actors_data: List[Dict[str, int]] = []
        movie_languages_data: List[Dict[str, int]] = []

        for i, (_, row) in enumerate(tqdm(data.iterrows(), total=data.shape[0], desc="Processing associations")):
            movie_id = movie_ids[i]

            for genre_name in row['genre'].split(','):
                genre_name = genre_name.strip()
                if genre_name:
                    genre = genre_map[genre_name]
                    movie_genres_data.append({"movie_id": movie_id, "genre_id": genre.id})

            for actor_name in row['crew'].split(','):
                actor_name = actor_name.strip()
                if actor_name:
                    actor = actor_map[actor_name]
                    movie_actors_data.append({"movie_id": movie_id, "actor_id": actor.id})

            for lang_name in row['orig_lang'].split(','):
                lang_name = lang_name.strip()
                if lang_name:
                    language = language_map[lang_name]
                    movie_languages_data.append({"movie_id": movie_id, "language_id": language.id})

        return movie_genres_data, movie_actors_data, movie_languages_data

    async def seed(self) -> None:
        """
        Main method to seed the database with movie data from the CSV.
        It pre-processes the CSV, prepares reference data (countries, genres, actors, languages),
        inserts all movies, then inserts many-to-many relationships (genres, actors, languages).
        """
        try:
            if self._db_session.in_transaction():
                print("Rolling back existing transaction.")
                await self._db_session.rollback()

            await self._seed_user_groups()

            data = self._preprocess_csv()

            country_map, genre_map, actor_map, language_map = await self._prepare_reference_data(data)

            movies_data = self._prepare_movies_data(data, country_map)

            result = await self._db_session.execute(
                insert(MovieModel).returning(MovieModel.id),
                movies_data
            )
            movie_ids = list(result.scalars().all())

            movie_genres_data, movie_actors_data, movie_languages_data = self._prepare_associations(
                data, movie_ids, genre_map, actor_map, language_map
            )

            await self._bulk_insert(MoviesGenresModel, movie_genres_data)
            await self._bulk_insert(ActorsMoviesModel, movie_actors_data)
            await self._bulk_insert(MoviesLanguagesModel, movie_languages_data)

            await self._db_session.commit()
            print("Seeding completed.")

        except SQLAlchemyError as e:
            print(f"An error occurred: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise


async def main() -> None:
    """
    The main async entry point for running the database seeder.
    Checks if the database is already populated, and if not, performs the seeding process.
    """
    settings = get_settings()
    async with get_db_contextmanager() as db_session:
        seeder = CSVDatabaseSeeder(settings.PATH_TO_MOVIES_CSV, db_session)

        if not await seeder.is_db_populated():
            try:
                await seeder.seed()
                print("Database seeding completed successfully.")
            except Exception as e:
                print(f"Failed to seed the database: {e}")
        else:
            print("Database is already populated. Skipping seeding.")


if __name__ == "__main__":
    asyncio.run(main())
