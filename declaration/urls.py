from django.urls import path
from . import views

app_name = 'declaration'

urlpatterns = [
    path('',                     views.dashboard,               name='dashboard'),
    path('lancer/',              views.lancer_declaration_view, name='lancer'),
    path('config-form/',         views.config_form_view,        name='config_form'),
    path('config/',              views.update_config_view,      name='update_config'),
    path('<int:pk>/',            views.detail_process,          name='detail'),
    path('<int:pk>/delete-form/', views.delete_form_view,       name='delete_form'),
    path('<int:pk>/delete/',      views.delete_process,         name='delete'),
]
