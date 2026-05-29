from django.shortcuts import render
from django.views.decorators.http import require_GET

from .services import get_sorties_detail, get_sorties_summary


@require_GET
def dashboard(request):
    rows = get_sorties_summary()
    return render(request, 'sortie/dashboard.html', {'rows': rows})


@require_GET
def detail_mois(request, monthdate):
    rows = get_sorties_detail(monthdate)
    montant_total = sum(float(r.get('montant_pret') or 0) for r in rows)
    return render(request, 'sortie/partials/detail_rows.html', {
        'monthdate':     monthdate,
        'rows':          rows,
        'montant_total': montant_total,
    })
