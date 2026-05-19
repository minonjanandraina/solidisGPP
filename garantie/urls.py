from django.urls import path
from . import views

app_name = 'garantie'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('lancer/', views.lancer_appel_view, name='lancer_appel'),
    path('<int:pk>/', views.detail_process, name='detail'),
    path('<int:pk>/statut-form/', views.statut_form_view, name='statut_form'),
    path('<int:pk>/statut/', views.update_statut, name='update_statut'),
]
