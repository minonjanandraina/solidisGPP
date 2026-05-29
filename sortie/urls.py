from django.urls import path

from . import views

app_name = 'sortie'

urlpatterns = [
    path('',                   views.dashboard,   name='dashboard'),
    path('<str:monthdate>/',   views.detail_mois, name='detail'),
]
