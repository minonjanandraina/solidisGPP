from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import CommissionProcess
from .services import lancer_commission


def _base_qs():
    return CommissionProcess.objects.annotate(
        details_count=Count('details'),
        com1_total=Coalesce(
            Sum('details__commission',
                filter=Q(details__commission_type__startswith='Commission 1')),
            0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        com2_total=Coalesce(
            Sum('details__commission',
                filter=Q(details__commission_type__startswith='Commission 2')),
            0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        com_total=Coalesce(
            Sum('details__commission'),
            0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    ).order_by('-date_from')


@require_GET
def dashboard(request):
    process_list = _base_qs().all()
    return render(request, 'commission/dashboard.html', {'process_list': process_list})


@require_POST
def lancer_commission_view(request):
    date_from = request.POST.get('date_from')
    date_to   = request.POST.get('date_to')

    error   = None
    process = None
    try:
        raw     = lancer_commission(date_from, date_to)
        process = _base_qs().get(pk=raw.pk)
    except Exception as e:
        error = str(e)

    return render(request, 'commission/partials/process_row.html', {
        'process': process,
        'error':   error,
    })


@require_GET
def statut_form_view(request, pk):
    process = get_object_or_404(CommissionProcess, pk=pk)
    return render(request, 'commission/partials/process_modal_form.html', {'process': process})


@require_POST
def update_statut(request, pk):
    process = get_object_or_404(CommissionProcess, pk=pk)
    nouveau_statut = request.POST.get('statut')
    if nouveau_statut in CommissionProcess.Statut.values:
        process.statut = nouveau_statut
        reference = request.POST.get('reference_solidis', '').strip()
        process.reference_solidis = reference or None
        process.save(update_fields=['statut', 'reference_solidis'])
    process = _base_qs().get(pk=pk)
    response = render(request, 'commission/partials/process_row.html', {'process': process})
    response['HX-Trigger'] = 'closeModal'
    return response


@require_GET
def delete_form_view(request, pk):
    process = get_object_or_404(CommissionProcess, pk=pk)
    return render(request, 'commission/partials/delete_modal.html', {'process': process})


@require_POST
def delete_process(request, pk):
    process = get_object_or_404(CommissionProcess, pk=pk)
    if request.POST.get('password', '') != 'Raz12Min@@':
        response = render(request, 'commission/partials/delete_modal.html', {
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
        CommissionProcess.objects.prefetch_related('details'),
        pk=pk,
    )
    return render(request, 'commission/detail.html', {'process': process})
