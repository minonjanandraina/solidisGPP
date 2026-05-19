from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST, require_GET

from .models import ProcesseAppelDeGarantie
from .services import lancer_appel


@require_GET
def dashboard(request):
    process_list = ProcesseAppelDeGarantie.objects.prefetch_related('situations', 'transactions').all()
    return render(request, 'garantie/dashboard.html', {'process_list': process_list})


@require_POST
def lancer_appel_view(request):
    date_from = request.POST.get('date_from')
    date_to   = request.POST.get('date_to')

    error = None
    process = None
    try:
        process = lancer_appel(date_from, date_to)
    except Exception as e:
        error = str(e)

    return render(request, 'garantie/partials/process_row.html', {
        'process': process,
        'error': error,
    })


@require_GET
def statut_form_view(request, pk):
    process = get_object_or_404(ProcesseAppelDeGarantie, pk=pk)
    return render(request, 'garantie/partials/process_modal_form.html', {'process': process})


@require_GET
def process_row_view(request, pk):
    process = get_object_or_404(
        ProcesseAppelDeGarantie.objects.prefetch_related('situations', 'transactions'),
        pk=pk,
    )
    return render(request, 'garantie/partials/process_row.html', {'process': process})


@require_POST
def update_statut(request, pk):
    process = get_object_or_404(ProcesseAppelDeGarantie, pk=pk)
    nouveau_statut = request.POST.get('statut')
    if nouveau_statut in ProcesseAppelDeGarantie.Statut.values:
        process.statut = nouveau_statut
        reference = request.POST.get('reference_solidis', '').strip()
        process.reference_solidis = reference or None
        process.save(update_fields=['statut', 'reference_solidis'])
    process.refresh_from_db()
    response = render(request, 'garantie/partials/process_row.html', {'process': process})
    response['HX-Trigger'] = 'closeModal'
    return response


@require_GET
def detail_process(request, pk):
    process = get_object_or_404(
        ProcesseAppelDeGarantie.objects.prefetch_related('situations', 'transactions'),
        pk=pk,
    )
    return render(request, 'garantie/detail.html', {'process': process})
