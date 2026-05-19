from django.urls import path
from . import views

app_name = 'recouvrement'

urlpatterns = [
    path('',                      views.dashboard,               name='dashboard'),
    path('lancer/',               views.lancer_recouvrement_view, name='lancer'),
    path('<int:pk>/',             views.detail_process,           name='detail'),
    path('<int:pk>/statut-form/', views.statut_form_view,         name='statut_form'),
    path('<int:pk>/statut/',      views.update_statut,            name='update_statut'),
    path('<int:pk>/delete-form/', views.delete_form_view,         name='delete_form'),
    path('<int:pk>/delete/',      views.delete_process,           name='delete'),
]
