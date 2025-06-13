from django.urls import path

from core.views import IndexView
from . import views

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('fetch/', views.download_dataset, name='fetch_dataset'),
    path('dataset/<int:pk>/', views.view_dataset, name='view_dataset'),
]
