import platform

import pandas as pd
import pyodbc


def _get_conx():
    driver = "ODBC Driver 17 for SQL Server" if platform.system() == "Linux" else "SQL Server"
    return pyodbc.connect(
        f"DRIVER={{{driver}}};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
    )


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
    df = pd.read_sql(sql, _get_conx())
    return df.to_dict('records') if not df.empty else []


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
      AND CONCAT(YEAR([reportDate]), '-', RIGHT(CONCAT('000', MONTH([reportDate])), 2)) = '{monthdate}'
    ORDER BY r.reportDate, l.AgreementDate desc
    """.format(monthdate=monthdate.replace("'", ""))
    df = pd.read_sql(sql, _get_conx())
    return df.to_dict('records') if not df.empty else []
