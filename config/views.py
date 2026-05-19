from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render

from commission.models import CommissionDetail, CommissionProcess
from garantie.models import ProcesseAppelDeGarantie
from recouvrement.models import RecouvrementProcess


def home_dashboard(request):
    # ── Appels de garantie ─────────────────────────────────────────
    g_recent = ProcesseAppelDeGarantie.objects.annotate(
        nb_sit=Count('situations', distinct=True),
        montant=Coalesce(
            Sum('situations__montant_appel_garanti'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    ).order_by('-date_from')[:5]

    g_agg = ProcesseAppelDeGarantie.objects.aggregate(
        count=Count('id'),
        montant_total=Coalesce(
            Sum('situations__montant_appel_garanti'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    )
    g_statuts = {
        s['statut']: s['n']
        for s in ProcesseAppelDeGarantie.objects.values('statut').annotate(n=Count('id'))
    }

    # ── Commissions ────────────────────────────────────────────────
    c_recent = CommissionProcess.objects.annotate(
        nb_det=Count('details', distinct=True),
        total=Coalesce(
            Sum('details__commission'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    ).order_by('-date_from')[:5]

    c_agg = CommissionProcess.objects.aggregate(
        count=Count('id'),
        total=Coalesce(
            Sum('details__commission'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    )
    c_com1 = CommissionDetail.objects.filter(
        commission_type__startswith='Commission 1',
    ).aggregate(
        t=Coalesce(Sum('commission'), 0, output_field=DecimalField(max_digits=18, decimal_places=2))
    )['t']
    c_com2 = CommissionDetail.objects.filter(
        commission_type__startswith='Commission 2',
    ).aggregate(
        t=Coalesce(Sum('commission'), 0, output_field=DecimalField(max_digits=18, decimal_places=2))
    )['t']
    c_statuts = {
        s['statut']: s['n']
        for s in CommissionProcess.objects.values('statut').annotate(n=Count('id'))
    }

    # ── Recouvrements ──────────────────────────────────────────────
    r_recent = RecouvrementProcess.objects.annotate(
        nb_trx=Count('transactions', distinct=True),
        total_rec=Coalesce(
            Sum('transactions__recouvrement_a_reverser'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    ).order_by('-date_from')[:5]

    r_agg = RecouvrementProcess.objects.aggregate(
        count=Count('id'),
        total_remb=Coalesce(
            Sum('transactions__total_remboursement_principale'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        total_rec=Coalesce(
            Sum('transactions__recouvrement_a_reverser'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    )
    r_statuts = {
        s['statut']: s['n']
        for s in RecouvrementProcess.objects.values('statut').annotate(n=Count('id'))
    }

    return render(request, 'home/dashboard.html', {
        'g_count':   g_agg['count'],
        'g_montant': g_agg['montant_total'],
        'g_statuts': g_statuts,
        'g_recent':  g_recent,

        'c_count':   c_agg['count'],
        'c_total':   c_agg['total'],
        'c_com1':    c_com1,
        'c_com2':    c_com2,
        'c_statuts': c_statuts,
        'c_recent':  c_recent,

        'r_count':   r_agg['count'],
        'r_remb':    r_agg['total_remb'],
        'r_rec':     r_agg['total_rec'],
        'r_statuts': r_statuts,
        'r_recent':  r_recent,
    })
