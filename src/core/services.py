import os
import requests
import petl as etl
from datetime import datetime

from django.utils import timezone

from config import settings
from .models import Dataset

def transform_data(records):
    """
    Cleans and preprocesses Star Wars character data:
    - Adds `date` column based on `edited` field in format YYYY-MM-DD,
    - Resolves `homeworld` URLs to planet names with caching to avoid unnecessary fetches,
    - Drops fields: films, species, vehicles, starships, created, edited.
    """
    table = etl.fromdicts(records)
    table = etl.addfield(table, 'date', lambda rec: rec.get('edited', '')[:10])
    planet_cache = {}
    def get_planet_name(url):
        if not url:
            return ''
        if url in planet_cache:
            return planet_cache[url]
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            name = resp.json().get('name', url)
        except Exception:
            name = url
        planet_cache[url] = name
        return name
    table = etl.convert(table, 'homeworld', get_planet_name)
    table = etl.cutout(table, 'films', 'species', 'vehicles', 'starships', 'created', 'edited', 'url')
    return table

def fetch_and_store_characters():
    """
    Fetches full dataset of Star Wars characters from SWAPI,
    cleans and preprocesses data, saves to CSV and records metadata.
    """
    base_url = os.environ.get('SWAPI_URL', 'http://swapi:12345/api')
    url = f"{base_url}/people/"
    all_characters = []
    while url:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        all_characters.extend(data.get('results', []))
        url = data.get('next')
    table = transform_data(all_characters)
    data_dir = os.path.join(settings.BASE_DIR, 'data', 'characters')
    os.makedirs(data_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"swapi_characters_{timestamp}.csv"
    file_path = os.path.join(data_dir, filename)
    etl.tocsv(table, file_path)
    ds = Dataset(filename=filename, download_date=timezone.now())
    ds.save()
    return filename