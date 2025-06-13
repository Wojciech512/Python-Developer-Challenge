import os
import csv
import tempfile
import json
from unittest.mock import patch, MagicMock

import petl as etl

from django.conf import settings
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from django.utils import timezone

from core.models import Dataset
from core.services import (
    transform_data,
    fetch_and_store_characters,
    load_dataset_preview,
    aggregate_provided_dataset,
)


class ServicesTests(TestCase):
    def setUp(self):
        self.records = [
            {
                "name": "Luke",
                "edited": "2025-06-13T10:00:00Z",
                "homeworld": "http://api/planet/1/",
                "films": [],
                "species": [],
                "vehicles": [],
                "starships": [],
                "created": "2025-06-13",
                "url": "http://api/people/1/",
            },
            {
                "name": "Leia",
                "edited": "2025-06-12T09:00:00Z",
                "homeworld": "",
                "films": [],
                "species": [],
                "vehicles": [],
                "starships": [],
                "created": "2025-06-12",
                "url": "http://api/people/2/",
            },
        ]

    @patch("core.services.requests.get")
    def test_transform_data(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"name": "Tatooine"}
        mock_get.return_value = mock_resp

        table = transform_data(self.records)
        rows = list(etl.dicts(table))
        self.assertEqual(rows[0]["date"], "2025-06-13")
        self.assertEqual(rows[1]["date"], "2025-06-12")
        self.assertEqual(rows[0]["homeworld"], "Tatooine")
        self.assertEqual(rows[1]["homeworld"], "")
        for rec in rows:
            for f in [
                "films",
                "species",
                "vehicles",
                "starships",
                "created",
                "edited",
                "url",
            ]:
                self.assertNotIn(f, rec)

    @patch("core.services.requests.get")
    def test_fetch_and_store_characters(self, mock_get):
        page1 = MagicMock()
        page1.raise_for_status.return_value = None
        page1.json.return_value = {
            "results": [
                {
                    "name": "A",
                    "edited": "2025-01-01T00:00:00Z",
                    "homeworld": "",
                    "films": [],
                    "species": [],
                    "vehicles": [],
                    "starships": [],
                    "created": "2025-01-01",
                    "url": "",
                }
            ],
            "next": "http://api/next",
        }
        page2 = MagicMock()
        page2.raise_for_status.return_value = None
        page2.json.return_value = {
            "results": [
                {
                    "name": "B",
                    "edited": "2025-01-02T00:00:00Z",
                    "homeworld": "",
                    "films": [],
                    "species": [],
                    "vehicles": [],
                    "starships": [],
                    "created": "2025-01-02",
                    "url": "",
                }
            ],
            "next": None,
        }
        mock_get.side_effect = [page1, page2]
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(BASE_DIR=tmpdir):
                fname = fetch_and_store_characters()
                data_dir = os.path.join(tmpdir, "data", "characters")
                path = os.path.join(data_dir, fname)
                self.assertTrue(os.path.exists(path))
                ds = Dataset.objects.get(filename=fname)
                self.assertIsNotNone(ds.download_date)

    def test_load_dataset_preview_and_aggregate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = os.path.join(tmpdir, "data", "characters")
            os.makedirs(data_dir)
            fname = "test.csv"
            path = os.path.join(data_dir, fname)
            rows = [
                {"col1": "X", "col2": "1"},
                {"col1": "X", "col2": "2"},
                {"col1": "Y", "col2": "1"},
            ]

            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["col1", "col2"])
                writer.writeheader()
                writer.writerows(rows)
            with override_settings(BASE_DIR=tmpdir):
                preview = load_dataset_preview(fname, offset=0, limit=2)
                self.assertEqual(len(preview), 2)
                self.assertEqual(preview[0]["col1"], "X")
                more = load_dataset_preview(fname, offset=2, limit=2)
                self.assertEqual(len(more), 1)
                self.assertEqual(more[0]["col1"], "Y")
                agg = aggregate_provided_dataset(fname, ["col1"])
                counts = {row["col1"]: row["count"] for row in agg}
                self.assertEqual(counts, {"X": 2, "Y": 1})


class ViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("core.views.fetch_and_store_characters")
    def test_download_dataset_post(self, mock_fetch):
        mock_fetch.return_value = "file.csv"
        url = reverse("fetch_dataset")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok", "file": "file.csv"})
        mock_fetch.assert_called_once()

    def test_download_dataset_get_not_allowed(self):
        url = reverse("fetch_dataset")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_index_view(self):
        now = timezone.now()
        ds1 = Dataset.objects.create(filename="a.csv", download_date=now)
        older = now - timezone.timedelta(days=1)
        ds2 = Dataset.objects.create(filename="b.csv", download_date=older)
        url = reverse("index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        datasets = response.context["datasets"]
        self.assertEqual(datasets[0]["pk"], ds1.pk)
        self.assertEqual(datasets[1]["pk"], ds2.pk)
        self.assertIn("formatted_date", datasets[0])

    def test_view_dataset_and_load_more(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = os.path.join(tmpdir, "data", "characters")
            os.makedirs(data_dir)
            fname = "test2.csv"
            path = os.path.join(data_dir, fname)

            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["a", "b"])
                writer.writerow(["1", "2"])
            with override_settings(BASE_DIR=tmpdir):
                ds = Dataset.objects.create(
                    filename=fname, download_date=timezone.now()
                )

                url = reverse("view_dataset", args=[ds.pk])
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "detail.html")

                url_more = reverse("load_more_rows", args=[ds.pk])
                resp2 = self.client.get(f"{url_more}?offset=0")
                self.assertEqual(resp2.status_code, 200)
                data = resp2.json()["rows"]
                self.assertIsInstance(data, list)

    def test_aggregate_dataset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = os.path.join(tmpdir, "data", "characters")
            os.makedirs(data_dir)
            fname = "agg.csv"
            path = os.path.join(data_dir, fname)
            rows = [
                {"col": "X"},
                {"col": "Y"},
                {"col": "X"},
            ]
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["col"])
                writer.writeheader()
                writer.writerows(rows)
            with override_settings(BASE_DIR=tmpdir):
                ds = Dataset.objects.create(
                    filename=fname, download_date=timezone.now()
                )
                url = reverse("aggregate_dataset", args=[ds.pk])

                resp_get = self.client.get(url)
                self.assertEqual(resp_get.status_code, 405)

                resp_bad = self.client.post(
                    url, data=json.dumps({}), content_type="application/json"
                )
                self.assertJSONEqual(resp_bad.content, {"columns": [], "rows": []})

                payload = {"columns": ["col"]}
                resp = self.client.post(
                    url, data=json.dumps(payload), content_type="application/json"
                )
                self.assertEqual(resp.status_code, 200)
                result = resp.json()
                self.assertEqual(result["columns"], ["col"])
                self.assertIsInstance(result["rows"], list)
