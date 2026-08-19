from django.urls import include, path
from . import views

urlpatterns = [
    path('',               views.home_dashboard,                              name='home'),
    path('partials/encours-par/',    views.dash_encours_par,    name='dash_encours_par'),
    path('partials/bilan/',          views.dash_bilan,          name='dash_bilan'),
    path('partials/appels/',         views.dash_appels,         name='dash_appels'),
    path('partials/commissions/',    views.dash_commissions,    name='dash_commissions'),
    path('partials/recouvrements/',  views.dash_recouvrements,  name='dash_recouvrements'),
    path('partials/sorties/',        views.dash_sorties,        name='dash_sorties'),
    path('declaration/',   include('declaration.urls',  namespace='declaration')),
    path('garantie/',      include('garantie.urls',     namespace='garantie')),
    path('commission/',    include('commission.urls',   namespace='commission')),
    path('recouvrement/',  include('recouvrement.urls', namespace='recouvrement')),
    path('sortie/',        include('sortie.urls',       namespace='sortie')),
]
