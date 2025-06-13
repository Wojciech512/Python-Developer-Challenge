import os
import requests
import petl as etl
from datetime import datetime

from django.utils import timezone

from config import settings
from .models import Dataset

def fetch_and_store_characters():
    base_url = os.environ.get('SWAPI_URL', 'http://swapi:12345/api')
    people_url = f"{base_url}/people/"

    all_characters = []
    url = people_url
    while url:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        all_characters.extend(data.get('results', []))
        url = data.get('next')

    table = etl.fromdicts(all_characters)

    data_dir = os.path.join(settings.BASE_DIR, 'data/characters')
    os.makedirs(data_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"swapi_characters_{timestamp}.csv"

    file_path = os.path.join(data_dir, filename)
    etl.tocsv(table, file_path)

    dataset = Dataset(filename=filename, download_date=timezone.now())
    dataset.save()
    return filename
