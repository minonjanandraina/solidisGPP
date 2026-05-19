from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import RecouvrementProcess
from .services import lancer_recouvrement


def _base_qs():
    return RecouvrementProcess.objects.annotate(
        trx_count=Count('transactions'),
        total_remboursement=Coalesce(
            Sum('transactions__total_remboursement_principale'),
            0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        total_recouvrement=Coalesce(
            Sum('transactions__recouvrement_a_reverser'),
            0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    ).order_by('-date_from')


@require_GET
def dashboard(request):
    process_list = _base_qs().all()
    return render(request, 'recouvrement/dashboard.html', {'process_list': process_list})


@require_POST
def lancer_recouvrement_view(request):
    date_from = request.POST.get('date_from')
    date_to   = request.POST.get('date_to')

    error   = None
    process = None
    try:
        raw     = lancer_recouvrement(date_from, date_to)
        process = _base_qs().get(pk=raw.pk)
    except Exception as e:
        error = str(e)

    return render(request, 'recouvrement/partials/process_row.html', {
        'process': process,
        'error':   error,
    })


@require_GET
def statut_form_view(request, pk):
    process = get_object_or_404(RecouvrementProcess, pk=pk)
    return render(request, 'recouvrement/partials/process_modal_form.html', {'process': process})


@require_POST
def update_statut(request, pk):
    process = get_object_or_404(RecouvrementProcess, pk=pk)
    nouveau_statut = request.POST.get('statut')
    if nouveau_statut in RecouvrementProcess.Statut.values:
        process.statut = nouveau_statut
        reference = request.POST.get('reference_solidis', '').strip()
        process.reference_solidis = reference or None
        process.save(update_fields=['statut', 'reference_solidis'])
    process = _base_qs().get(pk=pk)
    response = render(request, 'recouvrement/partials/process_row.html', {'process': process})
    response['HX-Trigger'] = 'closeModal'
    return response


@require_GET
def delete_form_view(request, pk):
    process = get_object_or_404(RecouvrementProcess, pk=pk)
    return render(request, 'recouvrement/partials/delete_modal.html', {'process': process})


@require_POST
def delete_process(request, pk):
    process = get_object_or_404(RecouvrementProcess, pk=pk)
    if request.POST.get('password', '') != 'Raz12Min@@':
        response = render(request, 'recouvrement/partials/delete_modal.html', {
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


@require_GET
def detail_process(request, pk):
    process = get_object_or_404(
        RecouvrementProcess.objects.prefetch_related('transactions'),
        pk=pk,
    )
    return render(request, 'recouvrement/detail.html', {'process': process})
