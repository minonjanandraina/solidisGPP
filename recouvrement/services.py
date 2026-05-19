import platform

import pandas as pd
import pyodbc
from django.db.models import Max

from .models import RecouvrementProcess, RecouvrementTransaction


def _get_conx():
    driver = "ODBC Driver 17 for SQL Server" if platform.system() == "Linux" else "SQL Server"
    return pyodbc.connect(
        f"DRIVER={{{driver}}};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
    )


def _get_last_allocation_id() -> int:
    result = RecouvrementTransaction.objects.aggregate(max_id=Max('last_allocation_id'))
    return result['max_id'] or 0


def _get_recouvrements(date_from: str, date_to: str, last_allocation_id: int) -> pd.DataFrame:
    sql = """
    SELECT
        r.IDCREDIT,
        r.loLoanID,
        l.AgreementNumber               AS agreement_number,
        l.AgreementDate                 AS agreement_date,
        MAX(l.LoanAmountCurrent)        AS loan_amount,
        MAX(r.Encours)                  AS encours_au_moment_appel,
        SUM(CASE WHEN lD.DebitType = 2 THEN lA.AmountCRY ELSE 0 END)     AS total_remboursement_principale,
        SUM(CASE WHEN lD.DebitType = 2 THEN lA.AmountCRY ELSE 0 END) / 2 AS recouvrement_a_reverser,
        MAX(lA.loloanAllocationID)      AS last_allocation_id
    FROM solidis.dbo.Solidis_loan_update_monthly_reports r
    JOIN cbs.dbo.loLoan l               ON l.loLoanID          = r.loLoanID
    JOIN CBS.dbo.loloancredit lc        ON lc.loLoanId         = l.loLoanID
    LEFT JOIN CBS.dbo.loloanAllocation lA ON lA.loLoanCreditID = lc.loLoanCreditID
    LEFT JOIN CBS.dbo.loloanDebit lD    ON lD.loLoanDebitID    = lA.loLoanDebitID
    WHERE r.DaysInArrears = 61
      AND r.reportDate BETWEEN '{dateFrom}' AND '{dateTo}'
      AND lA.Date > r.reportDate
      AND lD.DebitType = 2
      AND lA.loloanAllocationID > {lastId}
      AND CAST(lA.[Date] AS date) <= '{dateTo}'
    GROUP BY r.IDCREDIT, r.loLoanID, l.AgreementNumber, l.AgreementDate
    ORDER BY l.AgreementDate
    """.format(dateFrom=date_from, dateTo=date_to, lastId=last_allocation_id)
    return pd.read_sql(sql, _get_conx())


def lancer_recouvrement(date_from: str, date_to: str) -> RecouvrementProcess:
    last_id = _get_last_allocation_id()

    process = RecouvrementProcess.objects.create(
        date_from=date_from,
        date_to=date_to,
        statut=RecouvrementProcess.Statut.EN_COURS,
    )

    df = _get_recouvrements(date_from, date_to, last_id)
    df = df.dropna(subset=["loLoanID"])
    if not df.empty:
        RecouvrementTransaction.objects.bulk_create([
            RecouvrementTransaction(
                process=process,
                idcredit=row["IDCREDIT"] if pd.notna(row["IDCREDIT"]) else "",
                lo_loan_id=int(row["loLoanID"]),
                agreement_number=row.get("agreement_number"),
                agreement_date=row.get("agreement_date"),
                loan_amount=row.get("loan_amount"),
                encours_au_moment_appel=row.get("encours_au_moment_appel"),
                total_remboursement_principale=row["total_remboursement_principale"],
                recouvrement_a_reverser=row["recouvrement_a_reverser"],
                last_allocation_id=int(row["last_allocation_id"]) if pd.notna(row.get("last_allocation_id")) else None,
            )
            for _, row in df.iterrows()
        ])

    process.statut = RecouvrementProcess.Statut.SOUMIS
    process.save(update_fields=["statut"])

    return process
