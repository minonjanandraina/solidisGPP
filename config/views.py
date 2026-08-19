from collections import defaultdict
from decimal import Decimal

from django.db import connection
from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET

from commission.models import CommissionDetail, CommissionProcess
from garantie.models import ProcesseAppelDeGarantie
from recouvrement.models import RecouvrementProcess

PARTIAL_CACHE_SECONDS = 60 * 15

_MOIS_FR = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin',
            'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']


def _fmt_amount(value):
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def _fmt_pct(value):
    if value is None:
        return "—"
    return f"{float(value) * 100:.2f}".replace(".", ",") + " %"


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
        data = dict(zip(keys, row))
        for k in ('encours_total', 'par1', 'par30', 'par60'):
            data[f'{k}_fmt'] = _fmt_amount(data[k])
        for k in ('par1_pct', 'par30_pct', 'par60_pct'):
            data[f'{k}_fmt'] = _fmt_pct(data[k])
        return data
    except Exception:
        return None


def _month_label(d):
    return f"{_MOIS_FR[d.month - 1]} {d.year}"


def _get_solde_evolution():
    """Solde net PAMF (reçu - payé) regroupé par mois (date_from des process)."""
    recu_par_mois = defaultdict(Decimal)
    paye_par_mois = defaultdict(Decimal)

    g_rows = ProcesseAppelDeGarantie.objects.exclude(
        statut=ProcesseAppelDeGarantie.Statut.REJETE,
    ).annotate(
        montant=Coalesce(Sum('situations__montant_appel_garanti'), 0,
                          output_field=DecimalField(max_digits=18, decimal_places=2)),
    ).values('date_from', 'montant')
    for row in g_rows:
        recu_par_mois[row['date_from'].replace(day=1)] += row['montant']

    c_rows = CommissionProcess.objects.exclude(
        statut=CommissionProcess.Statut.REJETE,
    ).annotate(
        total=Coalesce(Sum('details__commission'), 0,
                        output_field=DecimalField(max_digits=18, decimal_places=2)),
    ).values('date_from', 'total')
    for row in c_rows:
        paye_par_mois[row['date_from'].replace(day=1)] += row['total']

    r_rows = RecouvrementProcess.objects.exclude(
        statut=RecouvrementProcess.Statut.REJETE,
    ).annotate(
        total_rec=Coalesce(Sum('transactions__recouvrement_a_reverser'), 0,
                            output_field=DecimalField(max_digits=18, decimal_places=2)),
    ).values('date_from', 'total_rec')
    for row in r_rows:
        paye_par_mois[row['date_from'].replace(day=1)] += row['total_rec']

    mois = sorted(set(recu_par_mois) | set(paye_par_mois), reverse=True)
    evolution = []
    for m in mois:
        recu  = recu_par_mois.get(m, Decimal('0'))
        paye  = paye_par_mois.get(m, Decimal('0'))
        solde = recu - paye
        evolution.append({
            'label':          _month_label(m),
            'recu_fmt':       _fmt_amount(recu),
            'paye_fmt':       _fmt_amount(paye),
            'solde_fmt':      _fmt_amount(solde),
            'solde_positive': solde >= 0,
        })
    return evolution


def home_dashboard(request):
    """Coquille de la page : ne fait aucune requête lourde.
    Chaque section se charge ensuite de façon indépendante via HTMX."""
    return render(request, 'home/dashboard.html')


@require_GET
@cache_page(PARTIAL_CACHE_SECONDS)
def dash_encours_par(request):
    return render(request, 'home/partials/_encours_par.html', {
        'encours_par': _get_encours_par(),
    })


@require_GET
@cache_page(PARTIAL_CACHE_SECONDS)
def dash_appels(request):
    g_qs = ProcesseAppelDeGarantie.objects.exclude(statut=ProcesseAppelDeGarantie.Statut.REJETE)

    g_recent = g_qs.annotate(
        nb_sit=Count('situations', distinct=True),
        montant=Coalesce(
            Sum('situations__montant_appel_garanti'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    ).order_by('-date_from')[:5]

    g_agg = g_qs.aggregate(
        count=Count('id', distinct=True),
        montant_total=Coalesce(
            Sum('situations__montant_appel_garanti'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    )
    g_statuts = {
        s['statut']: s['n']
        for s in g_qs.values('statut').annotate(n=Count('id'))
    }
    for p in g_recent:
        p.montant_fmt = _fmt_amount(p.montant)

    return render(request, 'home/partials/_appels.html', {
        'g_count':       g_agg['count'],
        'g_montant_fmt': _fmt_amount(g_agg['montant_total']),
        'g_statuts':     g_statuts,
        'g_recent':      g_recent,
    })


@require_GET
@cache_page(PARTIAL_CACHE_SECONDS)
def dash_commissions(request):
    c_qs = CommissionProcess.objects.exclude(statut=CommissionProcess.Statut.REJETE)

    c_recent = c_qs.annotate(
        nb_det=Count('details', distinct=True),
        total=Coalesce(
            Sum('details__commission'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    ).order_by('-date_from')[:5]

    c_agg = c_qs.aggregate(
        count=Count('id', distinct=True),
        total=Coalesce(
            Sum('details__commission'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    )
    c_com1 = CommissionDetail.objects.filter(
        commission_type__startswith='Commission 1',
    ).exclude(
        process__statut=CommissionProcess.Statut.REJETE,
    ).aggregate(
        t=Coalesce(Sum('commission'), 0, output_field=DecimalField(max_digits=18, decimal_places=2))
    )['t']
    c_com2 = CommissionDetail.objects.filter(
        commission_type__startswith='Commission 2',
    ).exclude(
        process__statut=CommissionProcess.Statut.REJETE,
    ).aggregate(
        t=Coalesce(Sum('commission'), 0, output_field=DecimalField(max_digits=18, decimal_places=2))
    )['t']
    c_statuts = {
        s['statut']: s['n']
        for s in c_qs.values('statut').annotate(n=Count('id'))
    }
    for p in c_recent:
        p.total_fmt = _fmt_amount(p.total)

    return render(request, 'home/partials/_commissions.html', {
        'c_count':       c_agg['count'],
        'c_total_fmt':   _fmt_amount(c_agg['total']),
        'c_com1_fmt':    _fmt_amount(c_com1),
        'c_com2_fmt':    _fmt_amount(c_com2),
        'c_statuts':     c_statuts,
        'c_recent':      c_recent,
    })


@require_GET
@cache_page(PARTIAL_CACHE_SECONDS)
def dash_recouvrements(request):
    r_qs = RecouvrementProcess.objects.exclude(statut=RecouvrementProcess.Statut.REJETE)

    r_recent = r_qs.annotate(
        nb_trx=Count('transactions', distinct=True),
        total_rec=Coalesce(
            Sum('transactions__recouvrement_a_reverser'), 0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    ).order_by('-date_from')[:5]

    r_agg = r_qs.aggregate(
        count=Count('id', distinct=True),
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
        for s in r_qs.values('statut').annotate(n=Count('id'))
    }
    for p in r_recent:
        p.total_rec_fmt = _fmt_amount(p.total_rec)

    return render(request, 'home/partials/_recouvrements.html', {
        'r_count':     r_agg['count'],
        'r_remb_fmt':  _fmt_amount(r_agg['total_remb']),
        'r_rec_fmt':   _fmt_amount(r_agg['total_rec']),
        'r_statuts':   r_statuts,
        'r_recent':    r_recent,
    })


@require_GET
@cache_page(PARTIAL_CACHE_SECONDS)
def dash_sorties(request):
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

    for r in s_recent:
        r['montant_sortie_fmt'] = _fmt_amount(r.get('montant_sortie'))

    return render(request, 'home/partials/_sorties.html', {
        's_count':       s_count,
        's_montant_fmt': _fmt_amount(s_montant),
        's_recent':      s_recent,
    })


@require_GET
@cache_page(PARTIAL_CACHE_SECONDS)
def dash_bilan(request):
    # Flux entrants pour PAMF : appel de garantie (SOLIDIS paie PAMF = Encours * 0.5)
    # Flux sortants pour PAMF : commissions (1.5% Encours) + part SOLIDIS sur recouvrement (50%)
    pamf_recu = ProcesseAppelDeGarantie.objects.exclude(
        statut=ProcesseAppelDeGarantie.Statut.REJETE,
    ).aggregate(
        t=Coalesce(Sum('situations__montant_appel_garanti'), 0,
                   output_field=DecimalField(max_digits=18, decimal_places=2))
    )['t']
    c_total = CommissionProcess.objects.exclude(
        statut=CommissionProcess.Statut.REJETE,
    ).aggregate(
        t=Coalesce(Sum('details__commission'), 0,
                   output_field=DecimalField(max_digits=18, decimal_places=2))
    )['t']
    r_total_rec = RecouvrementProcess.objects.exclude(
        statut=RecouvrementProcess.Statut.REJETE,
    ).aggregate(
        t=Coalesce(Sum('transactions__recouvrement_a_reverser'), 0,
                   output_field=DecimalField(max_digits=18, decimal_places=2))
    )['t']

    pamf_paye  = c_total + r_total_rec
    pamf_solde = pamf_recu - pamf_paye

    return render(request, 'home/partials/_bilan.html', {
        'pamf_recu_fmt':    _fmt_amount(pamf_recu),
        'pamf_paye_fmt':    _fmt_amount(pamf_paye),
        'pamf_solde_fmt':   _fmt_amount(pamf_solde),
        'pamf_solde':       pamf_solde,
        'solde_evolution':  _get_solde_evolution(),
    })
