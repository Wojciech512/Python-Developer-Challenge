import os
from datetime import datetime

import petl as etl
import requests
from django.utils import timezone
from django.conf import settings
from .models import Dataset


def transform_data(records):
    """
    Cleans and preprocesses Star Wars character data:
    - Adds `date` column based on `edited` field in format YYYY-MM-DD,
    - Resolves `homeworld` URLs to planet names with caching to avoid unnecessary fetches,
    - Drops fields: films, species, vehicles, starships, created, edited.
    """
    table = etl.fromdicts(records)
    table = etl.addfield(table, "date", lambda rec: rec.get("edited", "")[:10])
    planet_cache = {}

    def get_planet_name(url):
        if not url:
            return ""
        if url in planet_cache:
            return planet_cache[url]
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            name = resp.json().get("name", url)
        except Exception:
            name = url
        planet_cache[url] = name
        return name

    table = etl.convert(table, "homeworld", get_planet_name)
    table = etl.cutout(
        table,
        "films",
        "species",
        "vehicles",
        "starships",
        "created",
        "edited",
        "url",
    )
    return table


def fetch_and_store_characters():
    """
    Fetches full dataset of Star Wars characters from SWAPI,
    cleans and preprocesses data, saves to CSV and records metadata.
    """
    base_url = os.environ.get("SWAPI_URL", "http://swapi:12345/api")
    url = f"{base_url}/people/"
    all_characters = []

    while url:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        all_characters.extend(data.get("results", []))
        url = data.get("next")

    table = transform_data(all_characters)
    data_dir = os.path.join(settings.BASE_DIR, "data", "characters")
    os.makedirs(data_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"swapi_characters_{timestamp}.csv"

    file_path = os.path.join(data_dir, filename)
    etl.tocsv(table, file_path)

    ds = Dataset(filename=filename, download_date=timezone.now())
    ds.save()
    return filename


def load_dataset_preview(filename, offset=0, limit=10):
    """
    Loads a portion of data from a CSV file: returns `limit`
    rows starting from row `offset` (0-based).
    Returns a list of dictionaries (each record is a dict column>value).
    """
    data_dir = os.path.join(settings.BASE_DIR, "data", "characters")
    path = os.path.join(data_dir, filename)
    table = etl.fromcsv(path)
    if offset == 0:
        subset = etl.head(table, limit)
    else:
        subset = etl.rowslice(table, offset, offset + limit)
    return list(subset.dicts())


def aggregate_provided_dataset(filename, columns):
    """
    Counts the occurrences of value combinations for selected columns.
    Returns a list of dictionaries: each {col1: val1, col2: val2, ..., 'count': n}.
    """
    data_dir = os.path.join(settings.BASE_DIR, "data", "characters")
    path = os.path.join(data_dir, filename)
    table = etl.fromcsv(path)
    agg_table = etl.aggregate(table, key=columns, aggregation=len)
    agg_table = etl.rename(agg_table, {"value": "count"})
    agg_table = etl.sort(agg_table, "count", reverse=True)
    return list(agg_table.dicts())
