from django.urls import path

from core.views import IndexView

from . import views

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("fetch/", views.download_dataset, name="fetch_dataset"),
    path("dataset/<int:pk>/", views.view_dataset, name="view_dataset"),
    path("dataset/<int:pk>/load_more/", views.load_more_rows, name="load_more_rows"),
    path(
        "dataset/<int:pk>/aggregate/", views.aggregate_dataset, name="aggregate_dataset"
    ),
]
