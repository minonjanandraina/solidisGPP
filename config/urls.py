from django.urls import include, path
from . import views

urlpatterns = [
    path('',               views.home_dashboard,                              name='home'),
    path('garantie/',      include('garantie.urls',     namespace='garantie')),
    path('commission/',    include('commission.urls',   namespace='commission')),
    path('recouvrement/',  include('recouvrement.urls', namespace='recouvrement')),
]
