from django.contrib import admin
from django.urls import path, include

from Simulation import views

urlpatterns = [
    path('', views.index, name="Index")
]
