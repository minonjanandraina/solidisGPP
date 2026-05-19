import platform

import pandas as pd
import pyodbc

from .models import CommissionDetail, CommissionProcess


def _get_conx():
    driver = "ODBC Driver 17 for SQL Server" if platform.system() == "Linux" else "SQL Server"
    return pyodbc.connect(
        f"DRIVER={{{driver}}};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
    )


def _get_commissions(date_from: str, date_to: str) -> pd.DataFrame:
    sql = """
    SELECT
        r.loLoanID AS id,
        r.IDCREDIT,
        r.loLoanID,
        r.Encours,
        r.Encours * 0.015 AS commission,
        r.DaysInArrears,
        r.reportDate,
        'Commission 2 - 1.5%' AS commission_type
    FROM solidis.dbo.Solidis_loan_update_monthly_reports r
    WHERE r.DaysInArrears = 30
    AND r.reportDate BETWEEN '{dateFrom}' AND '{dateTo}'

    UNION

    SELECT
        loLoanID AS id,
        [ID CREDIT] AS IDCREDIT,
        [LOLOANID] AS loLoanID,
        [MONTANT] AS Encours,
        [MONTANT] * 0.015 AS commission,
        0 AS DaysInArrears,
        [DATOUV] AS reportDate,
        'Commission 1 - 1.5%' AS commission_type
    FROM solidis.dbo.Solidis_initial_loan
    WHERE CAST([DATOUV] AS date) BETWEEN '{dateFrom}' AND '{dateTo}'
    """.format(dateFrom=date_from, dateTo=date_to)
    return pd.read_sql(sql, _get_conx())


def lancer_commission(date_from: str, date_to: str) -> CommissionProcess:
    process = CommissionProcess.objects.create(
        date_from=date_from,
        date_to=date_to,
        statut=CommissionProcess.Statut.EN_COURS,
    )

    df = _get_commissions(date_from, date_to)
    df = df.dropna(subset=["loLoanID"])
    if not df.empty:
        CommissionDetail.objects.bulk_create([
            CommissionDetail(
                process=process,
                idcredit=row["IDCREDIT"] if pd.notna(row["IDCREDIT"]) else "",
                lo_loan_id=int(row["loLoanID"]),
                encours=row["Encours"],
                commission=row["commission"],
                commission_type=row["commission_type"],
                days_in_arrears=int(row["DaysInArrears"]) if pd.notna(row["DaysInArrears"]) else 0,
                report_date=row["reportDate"],
            )
            for _, row in df.iterrows()
        ])

    process.statut = CommissionProcess.Statut.SOUMIS
    process.save(update_fields=["statut"])

    return process
