from django.db import connection


def _dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_sorties_summary() -> list:
    """Retourne le résumé mensuel des sorties en portefeuille (Encours = 0)."""
    sql = """
    SELECT
        CONCAT(YEAR([reportDate]), '-', RIGHT(CONCAT('000', MONTH([reportDate])), 2)) AS monthdate,
        COUNT(*)                 AS nb_prets,
        SUM(l.LoanAmountCurrent) AS montant_sortie
    FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports] r
    JOIN cbs.dbo.loLoan l ON l.loLoanID = r.loLoanID
    WHERE r.Encours = 0
    GROUP BY CONCAT(YEAR([reportDate]), '-', RIGHT(CONCAT('000', MONTH([reportDate])), 2))
    ORDER BY CONCAT(YEAR([reportDate]), '-', RIGHT(CONCAT('000', MONTH([reportDate])), 2)) desc
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return _dictfetchall(cursor)


def get_sorties_detail(monthdate: str) -> list:
    """Retourne le détail des prêts sortis pour un mois donné (format YYYY-MM)."""
    sql = """
    SELECT
        l.AgreementDate       AS date_decaissement,
        l.MaturityDateCurrent AS date_echeance,
        r.reportDate          AS date_sortie,
        l.AgreementNumber     AS idcredit,
        l.LoanAmountCurrent   AS montant_pret,
        l.loLoanID
    FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports] r
    JOIN cbs.dbo.loLoan l ON l.loLoanID = r.loLoanID
    WHERE r.Encours = 0
      AND CONCAT(YEAR([reportDate]), '-', RIGHT(CONCAT('000', MONTH([reportDate])), 2)) = %s
    ORDER BY r.reportDate, l.AgreementDate desc
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [monthdate])
        return _dictfetchall(cursor)
