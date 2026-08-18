import calendar
import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.formats import date_format
from django.views.decorators.http import require_GET, require_POST

from .models import DeclarationProcess
from .services import (
    get_config,
    get_emg_summary,
    get_f2_declared_entries,
    lancer_declaration,
    update_config,
)


@require_GET
def dashboard(request):
    process_list = DeclarationProcess.objects.all()
    return render(request, 'declaration/dashboard.html', {
        'process_list': process_list,
        'config': get_config(),
    })


@require_POST
def lancer_declaration_view(request):
    mois = request.POST.get('mois')  # format "YYYY-MM"

    error         = None
    processes     = []
    periode_label = mois or ''
    try:
        annee, mois_num = (int(x) for x in (mois or '').split('-'))
        date_from = datetime.date(annee, mois_num, 1)
        date_to   = datetime.date(annee, mois_num, calendar.monthrange(annee, mois_num)[1])
        periode_label = date_format(date_from, "F Y")
        processes = lancer_declaration(date_from.isoformat(), date_to.isoformat())
    except (TypeError, ValueError):
        error = "Mois invalide."
    except Exception as e:
        error = str(e)

    return render(request, 'declaration/partials/process_rows.html', {
        'processes':     list(reversed(processes)),
        'log_processes': processes,
        'periode_label': periode_label,
        'error':         error,
        'config':        get_config(),
    })


@require_GET
def config_form_view(request):
    config = get_config()
    return render(request, 'declaration/partials/config_modal_form.html', {
        'config': config,
        'plafond_emg_raw': str(config.plafond_emg),
        'seuil_reprise_pct_raw': str(float(config.seuil_reprise_pct) * 100),
    })


@require_POST
def update_config_view(request):
    plafond_emg       = request.POST.get('plafond_emg')
    seuil_reprise_pct = request.POST.get('seuil_reprise_pct')

    error = None
    try:
        seuil = float(seuil_reprise_pct)
        if seuil > 1:  # saisie en pourcentage (ex: 80) plutôt qu'en fraction (0.80)
            seuil = seuil / 100
        config = update_config(float(plafond_emg), seuil)
    except (TypeError, ValueError):
        config = get_config()
        error = "Valeurs invalides."

    response = render(request, 'declaration/partials/config_panel.html', {
        'config': config,
        'error':  error,
    })
    if not error:
        response['HX-Trigger'] = 'closeModal'
    return response


@require_GET
def detail_process(request, pk):
    process = get_object_or_404(DeclarationProcess, pk=pk)
    f2_entries = get_f2_declared_entries(str(process.date), str(process.date))
    emg_summary = get_emg_summary(str(process.date), str(process.date))
    return render(request, 'declaration/detail.html', {
        'process':     process,
        'f2_entries':  f2_entries,
        'emg_summary': emg_summary,
    })


@require_GET
def delete_form_view(request, pk):
    process = get_object_or_404(DeclarationProcess, pk=pk)
    return render(request, 'declaration/partials/delete_modal.html', {'process': process})


@require_POST
def delete_process(request, pk):
    process = get_object_or_404(DeclarationProcess, pk=pk)
    if request.POST.get('password', '') != 'Raz12Min@@':
        response = render(request, 'declaration/partials/delete_modal.html', {
            'process': process,
            'error': 'Mot de passe incorrect.',
        })
        response['HX-Retarget'] = '#modal-body'
        response['HX-Reswap'] = 'innerHTML'
        return response
    process.delete()
    response = HttpResponse('')
    response['HX-Trigger'] = 'closeModal'
    return response
