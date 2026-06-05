from django.db import connection
from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render

from commission.models import CommissionDetail, CommissionProcess
from garantie.models import ProcesseAppelDeGarantie
from recouvrement.models import RecouvrementProcess


def _get_encours_par():
    sql = """
    SELECT
        [reportDate],
        SUM([Encours])                                                                    AS encours_total,
        SUM(CASE WHEN [DaysInArrears] <= 0 THEN [Encours] ELSE 0 END)                    AS encours_sain,
        SUM(CASE WHEN [DaysInArrears] >  0 and [DaysInArrears] <=120  THEN [Encours] ELSE 0 END)                    AS par1,
        SUM(CASE WHEN [DaysInArrears] >= 30 and [DaysInArrears] <=120 THEN [Encours] ELSE 0 END)                   AS par30,
        SUM(CASE WHEN [DaysInArrears] >  60 and [DaysInArrears] <= 120 THEN [Encours] ELSE 0 END)                   AS par60,
        SUM(CASE WHEN [DaysInArrears] >  0 and [DaysInArrears] <=120  THEN [Encours] ELSE 0 END)
            / NULLIF(SUM([Encours]), 0)                                            AS par1_pct,
        SUM(CASE WHEN [DaysInArrears] >= 30 and [DaysInArrears] <=120 THEN [Encours] ELSE 0 END)
            / NULLIF(SUM([Encours]), 0)                                             AS par30_pct,
        SUM(CASE WHEN [DaysInArrears] >  60   THEN [Encours] ELSE 0 END)
            / NULLIF(SUM([Encours]), 0)                                                 AS par60_pct
    FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports]
    WHERE [reportDate] = (
        SELECT MAX([reportDate]) FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports]
    )
    GROUP BY [reportDate]
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
        if row is None:
            return None
        keys = ['report_date', 'encours_total', 'encours_sain',
                'par1', 'par30', 'par60', 'par1_pct', 'par30_pct', 'par60_pct']
        print(dict(zip(keys, row)))
        return dict(zip(keys, row))
    except Exception:
        return None


def home_dashboard(request):
    # ── Encours & PAR (dernière date disponible) ───────────────────
    encours_par = _get_encours_par()

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

    # ── Sorties en portefeuille ───────────────────────────────────
    try:
        from sortie.services import get_sorties_summary
        _s_data   = get_sorties_summary()
        s_count   = len(_s_data)
        s_montant = sum(float(r.get('montant_sortie') or 0) for r in _s_data)
        s_recent  = _s_data[-5:][::-1]
    except Exception:
        s_count   = 0
        s_montant = 0.0
        s_recent  = []

    return render(request, 'home/dashboard.html', {
        'encours_par': encours_par,

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

        's_count':   s_count,
        's_montant': s_montant,
        's_recent':  s_recent,
    })
